from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite

from api.ws import manager as ws_manager
from core.sqlite import DB_PATH
from models.sensor import SensorPayload

# -----------------------------------------------------------------------------
# Thresholds — adjust these as needed
# -----------------------------------------------------------------------------
MAX_TEMPERATURE  = 35.0    # °C
MAX_POWER_W      = 3000.0  # Watts
MAX_AIR_QUALITY  = 1000.0  # ppm CO2
MIN_COMFORT      = 30.0    # 0–100 comfort score


# -----------------------------------------------------------------------------
# Internal dataclass — one detected anomaly
# -----------------------------------------------------------------------------
@dataclass
class Anomaly:
    type:     str
    message:  str
    severity: Literal["WARNING", "CRITICAL"]


# -----------------------------------------------------------------------------
# Rule engine — returns a list of anomalies found in one payload
# -----------------------------------------------------------------------------
def detect(payload: SensorPayload, room_mode: str) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    env   = payload.environment
    power = payload.power
    occ   = payload.occupancy

    # Rule 1 — high temperature
    if env.temperature > MAX_TEMPERATURE:
        anomalies.append(Anomaly(
            type="HIGH_TEMP",
            message=f"Temperature {env.temperature}°C exceeds {MAX_TEMPERATURE}°C",
            severity="WARNING",
        ))

    # Rule 2 — power spike
    if power.power > MAX_POWER_W:
        anomalies.append(Anomaly(
            type="POWER_SPIKE",
            message=f"Power consumption {power.power}W exceeds {MAX_POWER_W}W",
            severity="WARNING",
        ))

    # Rule 3 — bad air quality
    if env.air_quality > MAX_AIR_QUALITY:
        anomalies.append(Anomaly(
            type="BAD_AIR",
            message=f"Air quality {env.air_quality} ppm exceeds {MAX_AIR_QUALITY} ppm",
            severity="WARNING",
        ))

    # Rule 4 — low comfort score
    if env.comfort_score < MIN_COMFORT:
        anomalies.append(Anomaly(
            type="LOW_COMFORT",
            message=f"Comfort score {env.comfort_score} is below minimum {MIN_COMFORT}",
            severity="WARNING",
        ))

    # Rule 5 — unexpected presence during holiday
    # Someone is in the room but the system is in HOLIDAY mode
    if room_mode == "HOLIDAY" and occ.state == "OCCUPIED":
        anomalies.append(Anomaly(
            type="UNEXPECTED_PRESENCE",
            message=f"Room is in HOLIDAY mode but {occ.estimated_people} person(s) detected",
            severity="CRITICAL",
        ))

    return anomalies


# -----------------------------------------------------------------------------
# Save anomalies to SQLite notifications table
# Called from the MQTT subscriber (not a FastAPI endpoint, so no Depends)
# -----------------------------------------------------------------------------
async def check_and_notify(payload: SensorPayload) -> None:
    """
    Run the rule engine on a payload.
    If anomalies are found, save them as notifications in SQLite.
    """
    # Get the room's current mode from SQLite
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT mode FROM rooms WHERE room_id = ?",
            (payload.room_id,)
        )
        row = await cursor.fetchone()

        # If the room isn't registered yet, skip anomaly checks
        if row is None:
            return

        room_mode = row["mode"]

    # Run the rules
    anomalies = detect(payload, room_mode)

    if not anomalies:
        return

    # Save all detected anomalies as notifications
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for anomaly in anomalies:
            await db.execute(
                """
                INSERT INTO notifications (room_id, type, message, severity, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (payload.room_id, anomaly.type, anomaly.message, anomaly.severity, now),
            )
            print(
                f"[ANOMALY] [{anomaly.severity}] room={payload.room_id} "
                f"type={anomaly.type} → {anomaly.message}"
            )

            # Push alert to dashboard in real time
            await ws_manager.broadcast("notification", {
                "room_id":  payload.room_id,
                "type":     anomaly.type,
                "message":  anomaly.message,
                "severity": anomaly.severity,
                "created_at": now,
            })

        await db.commit()
