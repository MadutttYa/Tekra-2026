import json
from datetime import datetime

import aiomqtt
import aiosqlite

from core.sqlite import DB_PATH
from models.sensor import SensorPayload
from services.schedule_context import get_room_context

PRECOOL_SETPOINT = 26.0  # C — used when keeping room ready between classes


async def apply_schedule_control(payload: SensorPayload, client: aiomqtt.Client) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        c = await db.execute(
            "SELECT mode FROM rooms WHERE room_id = ?", (payload.room_id,)
        )
        row = await c.fetchone()

    if row is None:
        return

    if row["mode"] == "OVERRIDE":
        return

    ctx = await get_room_context(payload.room_id)
    occ = payload.occupancy.state

    if ctx["is_holiday"] or row["mode"] == "HOLIDAY":
        await _publish(client, payload.room_id, {
            "mode": "OVERRIDE",
            "actuators": {"lights": False, "ac": False, "master_relay": False},
        })
        await _set_status(payload.room_id, "HOLIDAY")
        return

    if ctx["is_active"]:
        await _set_status(payload.room_id, "ACTIVE")
        if occ in ("OCCUPIED", "TRANSITIONING"):
            await _publish(client, payload.room_id, {"mode": "AUTO"})
        else:
            await _publish(client, payload.room_id, {
                "mode": "OVERRIDE",
                "actuators": {"lights": False, "ac": True, "master_relay": False},
                "ac_setpoint": PRECOOL_SETPOINT,
            })
        return

    if ctx["in_buffer"]:
        await _set_status(payload.room_id, "DORMANT")
        if occ == "TRANSITIONING":
            await _publish(client, payload.room_id, {
                "mode": "OVERRIDE",
                "actuators": {"lights": False, "ac": True, "master_relay": False},
            })
        else:
            await _publish(client, payload.room_id, {
                "mode": "OVERRIDE",
                "actuators": {"lights": False, "ac": False, "master_relay": False},
            })
        return

    await _set_status(payload.room_id, "DORMANT")
    if occ == "EMPTY":
        await _publish(client, payload.room_id, {
            "mode": "OVERRIDE",
            "actuators": {"lights": False, "ac": False, "master_relay": False},
        })


async def _publish(client: aiomqtt.Client, room_id: str, cmd: dict) -> None:
    cmd["timestamp"] = datetime.utcnow().isoformat() + "Z"
    cmd["room_id"]   = room_id
    msg = json.dumps(cmd)
    for topic in [f"tekra/room/{room_id}/commands", f"tekra/wokwi/{room_id}/commands"]:
        try:
            await client.publish(topic, msg, qos=1)
        except Exception as e:
            print(f"[AutoCtrl] Publish error -> {topic}: {e}")
    print(f"[AutoCtrl] room={room_id} mode={cmd.get('mode')} "
          f"ac={cmd.get('actuators', {}).get('ac', '-')} "
          f"lights={cmd.get('actuators', {}).get('lights', '-')}")


async def _set_status(room_id: str, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE rooms SET status = ? WHERE room_id = ?", (status, room_id)
        )
        await db.commit()
