import aiomqtt
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from core.sqlite import get_sqlite
from models.command import RoomCommand
from mqtt.publisher import get_mqtt_client, publish_command

router = APIRouter(
    prefix="/rooms",
    tags=["Override / Commands"],
)


@router.post("/{room_id}/command")
async def send_command(
    room_id: str,
    body: RoomCommand,
    client: aiomqtt.Client = Depends(get_mqtt_client),
    db: aiosqlite.Connection = Depends(get_sqlite),
):
    """
    Send an actuator command to a room's ESP32.

    Rules:
    - Room must be in OVERRIDE or HOLIDAY mode.
    - In AUTO mode the system controls the room — manual commands are rejected.
    - If master_relay is True, all other actuator fields are ignored by the ESP32.
    """
    # Verify the room exists and check its current mode
    cursor = await db.execute(
        "SELECT mode FROM rooms WHERE room_id = ?",
        (room_id,)
    )
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_id}' not found")

    current_mode = row["mode"]

    if current_mode == "AUTO":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Room '{room_id}' is in AUTO mode. "
                "Switch to OVERRIDE first before sending manual commands."
            ),
        )

    # Build the payload (matches payload_server_to_esp.json)
    payload = {
        "mode":        body.mode,
        "actuators":   body.actuators.model_dump(),
        "ac_setpoint": body.ac_setpoint,
    }

    await publish_command(client, room_id, payload)

    return {
        "detail":  f"Command sent to room '{room_id}'",
        "topic":   f"tekra/room/{room_id}/commands",
        "payload": payload,
    }
