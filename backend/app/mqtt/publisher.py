import json
from datetime import datetime

import aiomqtt
from fastapi import HTTPException, Request


def get_mqtt_client(request: Request) -> aiomqtt.Client:
    client = request.app.state.mqtt_client
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="MQTT broker is temporarily unavailable — reconnecting, try again shortly.",
        )
    return client


async def publish_command(client: aiomqtt.Client, room_id: str, payload: dict) -> None:
    payload["timestamp"] = datetime.utcnow().isoformat() + "Z"
    payload["room_id"]   = room_id
    message = json.dumps(payload)

    for topic in [f"tekra/room/{room_id}/commands", f"tekra/wokwi/{room_id}/commands"]:
        await client.publish(topic, message, qos=1)
        print(f"[MQTT] Command sent -> {topic}")
