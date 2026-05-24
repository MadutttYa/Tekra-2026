import json
from datetime import datetime

import aiomqtt
from fastapi import HTTPException, Request


def get_mqtt_client(request: Request) -> aiomqtt.Client:
    """
    Dependency — retrieves the live MQTT client stored in app.state.
    Raises 503 if the subscriber is currently reconnecting.

    Use with FastAPI's Depends():
        client: aiomqtt.Client = Depends(get_mqtt_client)
    """
    client = request.app.state.mqtt_client
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="MQTT broker is temporarily unavailable — reconnecting, try again shortly.",
        )
    return client


async def publish_command(client: aiomqtt.Client, room_id: str, payload: dict) -> None:
    """
    Publish a command to a room's command topic.
    The ESP32 is subscribed to this topic and will act on the message.
    """
    topic = f"tekra/room/{room_id}/commands"

    # Add server timestamp to the payload
    payload["timestamp"] = datetime.utcnow().isoformat() + "Z"
    payload["room_id"]   = room_id

    message = json.dumps(payload)
    await client.publish(topic, message, qos=1)

    print(f"[MQTT] Command sent → {topic} | {message}")
