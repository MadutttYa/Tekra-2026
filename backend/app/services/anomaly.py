from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite

from api.ws import manager as ws_manager
from core.sqlite import DB_PATH
from models.sensor import SensorPayload

MAX_TEMPERATURE = 35.0    # C
MAX_POWER_W     = 3000.0  # W
MAX_AIR_QUALITY = 1000.0  # ppm
MIN_COMFORT     = 30.0    # 0-100


@dataclass
class Anomaly:
    type:     str
    message:  str
    severity: Literal["WARNING", "CRITICAL"]


def detect(payload: SensorPayload, room_mode: str) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    env   = payload.environment
    power = payload.power
    occ   = payload.occupancy

    if env.temperature > MAX_TEMPERATURE:
        anomalies.append(Anomaly(
            type="HIGH_TEMP",
            message=f"Temperature {env.temperature}C exceeds {MAX_TEMPERATURE}C",
            severity="WARNING",
        ))

    if power.power > MAX_POWER_W:
        anomalies.append(Anomaly(
            type="POWER_SPIKE",
            message=f"Power {power.power}W exceeds {MAX_POWER_W}W",
            severity="WARNING",
        ))

    if env.air_quality > MAX_AIR_QUALITY:
        anomalies.append(Anomaly(
            type="BAD_AIR",
            message=f"Air quality {env.air_quality} ppm exceeds {MAX_AIR_QUALITY} ppm",
            severity="WARNING",
        ))

    if env.comfort_score < MIN_COMFORT:
        anomalies.append(Anomaly(
            type="LOW_COMFORT",
            message=f"Comfort score {env.comfort_score} below minimum {MIN_COMFORT}",
            severity="WARNING",
        ))

    if room_mode == "HOLIDAY" and occ.state == "OCCUPIED":
        anomalies.append(Anomaly(
            type="UNEXPECTED_PRESENCE",
            message=f"Room is in HOLIDAY mode but {occ.estimated_people} person(s) detected",
            severity="CRITICAL",
        ))

    return anomalies


async def check_and_notify(payload: SensorPayload) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT mode FROM rooms WHERE room_id = ?", (payload.room_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return
        room_mode = row["mode"]

    anomalies = detect(payload, room_mode)
    if not anomalies:
        return

    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for anomaly in anomalies:
            await db.execute(
                "INSERT INTO notifications (room_id, type, message, severity, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload.room_id, anomaly.type, anomaly.message, anomaly.severity, now),
            )
            print(f"[ANOMALY] [{anomaly.severity}] room={payload.room_id} {anomaly.type}: {anomaly.message}")

            await ws_manager.broadcast("notification", {
                "room_id":    payload.room_id,
                "type":       anomaly.type,
                "message":    anomaly.message,
                "severity":   anomaly.severity,
                "created_at": now,
            })

        await db.commit()
