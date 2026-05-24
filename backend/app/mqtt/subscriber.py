import asyncio
import json

import aiomqtt
from fastapi import FastAPI
from pydantic import ValidationError

from api.ws import manager as ws_manager
from models.sensor import SensorPayload
from services.anomaly import check_and_notify
from services.auto_control import apply_schedule_control

TOPICS = [
    "tekra/room/+/telemetry",
    "tekra/wokwi/+/telemetry",
]

RECONNECT_DELAY = 5


async def handle_message(message: aiomqtt.Message, client: aiomqtt.Client | None = None) -> None:
    topic = str(message.topic)

    try:
        raw = json.loads(message.payload)
    except json.JSONDecodeError as e:
        print(f"[MQTT] Bad JSON on {topic}: {e}")
        return

    try:
        payload = SensorPayload(**raw)
    except ValidationError as e:
        print(f"[MQTT] Validation failed on {topic}: {e}")
        return

    source = topic.split("/")[1]

    print(
        f"[{source.upper()}] room={payload.room_id} "
        f"temp={payload.environment.temperature}C "
        f"people={payload.occupancy.estimated_people} ({payload.occupancy.state}) "
        f"power={payload.power.power}W"
    )

    await ws_manager.broadcast("sensor_update", {
        "room_id":     payload.room_id,
        "source":      source,
        "timestamp":   payload.timestamp.isoformat(),
        "environment": payload.environment.model_dump(),
        "power":       payload.power.model_dump(),
        "occupancy":   payload.occupancy.model_dump(),
    })

    if source == "room":
        await check_and_notify(payload)

    if client is not None:
        await apply_schedule_control(payload, client)


async def start_subscriber(hostname: str, port: int, app: FastAPI) -> None:
    while True:
        try:
            async with aiomqtt.Client(hostname=hostname, port=port) as client:
                app.state.mqtt_client = client

                for topic in TOPICS:
                    await client.subscribe(topic)
                    print(f"[MQTT] Subscribed to {topic}")

                async for message in client.messages:
                    await handle_message(message, client)

        except aiomqtt.MqttError as e:
            app.state.mqtt_client = None
            print(f"[MQTT] Connection lost: {e}. Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)

        except asyncio.CancelledError:
            print("[MQTT] Subscriber shutting down.")
            raise
