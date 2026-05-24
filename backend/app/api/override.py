import aiomqtt
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.command import RoomCommand
from mqtt.publisher import get_mqtt_client, publish_command

router = APIRouter(prefix="/rooms", tags=["Override / Commands"])


@router.post("/{room_id}/command")
async def send_command(
    room_id: str,
    body: RoomCommand,
    client: aiomqtt.Client = Depends(get_mqtt_client),
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    cursor = await db.execute("SELECT mode FROM rooms WHERE room_id = ?", (room_id,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    current_mode = row["mode"]

    # Master relay is an emergency cutoff — always allowed in any mode.
    # Activating it also forces the room into OVERRIDE so auto-control stops.
    if body.actuators.master_relay:
        await db.execute(
            "UPDATE rooms SET mode = 'OVERRIDE' WHERE room_id = ?", (room_id,)
        )
        await db.commit()
        current_mode = "OVERRIDE"

    is_mode_change_only = (
        body.mode is not None
        and not body.actuators.lights
        and not body.actuators.ac
        and not body.actuators.master_relay
    )

    if current_mode == "AUTO" and not is_mode_change_only:
        raise HTTPException(
            status_code=409,
            detail=f"Room '{room_id}' is in AUTO mode. Switch to OVERRIDE first.",
        )

    payload = {
        "mode":        body.mode,
        "actuators":   body.actuators.model_dump(),
        "ac_setpoint": body.ac_setpoint,
    }

    await publish_command(client, room_id, payload)

    return {
        "detail":  f"Command sent to room '{room_id}'",
        "payload": payload,
    }
