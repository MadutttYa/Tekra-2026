import asyncio
import json

import aiomqtt
from fastapi import FastAPI
from pydantic import ValidationError

from api.ws import manager as ws_manager
from models.sensor import SensorPayload
from services.anomaly import check_and_notify

# Topics to subscribe to
TOPICS = [
    "tekra/room/+/telemetry",
    "tekra/wokwi/+/telemetry",
]

RECONNECT_DELAY = 5   # seconds to wait before reconnecting


async def handle_message(message: aiomqtt.Message) -> None:
    """Parse and process one incoming MQTT message."""
    topic = str(message.topic)

    # Parse raw bytes → JSON dict
    try:
        raw = json.loads(message.payload)
    except json.JSONDecodeError as e:
        print(f"[MQTT] Bad JSON on topic {topic}: {e}")
        return

    # Validate against our schema
    try:
        payload = SensorPayload(**raw)
    except ValidationError as e:
        print(f"[MQTT] Payload validation failed on topic {topic}: {e}")
        return

    # Determine source from topic: "tekra/room/..." or "tekra/wokwi/..."
    source = topic.split("/")[1]   # "room" or "wokwi"

    # Log the incoming message
    print(
        f"[{source.upper()}] room={payload.room_id} | "
        f"temp={payload.environment.temperature}°C | "
        f"people={payload.occupancy.estimated_people} ({payload.occupancy.state}) | "
        f"power={payload.power.power}W"
    )

    # Broadcast live sensor data to all connected dashboard clients
    await ws_manager.broadcast("sensor_update", {
        "room_id":      payload.room_id,
        "source":       source,
        "timestamp":    payload.timestamp.isoformat(),
        "environment":  payload.environment.model_dump(),
        "power":        payload.power.model_dump(),
        "occupancy":    payload.occupancy.model_dump(),
    })

    # Run anomaly detection — saves notifications to SQLite if anything is wrong
    # Skip Wokwi simulation data so dummy data doesn't flood real notifications
    if source == "room":
        await check_and_notify(payload)


async def start_subscriber(hostname: str, port: int, app: FastAPI) -> None:
    """
    Subscribe to all telemetry topics and loop forever processing messages.
    Automatically reconnects if the broker drops the connection.
    Runs as a background asyncio task alongside the FastAPI server.
    """
    while True:
        try:
            print(f"[MQTT] Connecting to {hostname}:{port}...")
            async with aiomqtt.Client(hostname=hostname, port=port) as client:
                # Store the live client so endpoints can publish commands
                app.state.mqtt_client = client

                for topic in TOPICS:
                    await client.subscribe(topic)
                    print(f"[MQTT] Subscribed to {topic}")

                print("[MQTT] Subscriber ready — waiting for messages.")

                # This loop runs until the connection drops or the task is cancelled
                async for message in client.messages:
                    await handle_message(message)

        except aiomqtt.MqttError as e:
            app.state.mqtt_client = None
            print(f"[MQTT] Connection lost: {e}. Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)

        except asyncio.CancelledError:
            # App is shutting down — exit cleanly
            print("[MQTT] Subscriber shutting down.")
            raise
