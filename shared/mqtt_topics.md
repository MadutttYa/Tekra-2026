# MQTT Topic Structure

All topics are prefixed with `tekra/`. Real hardware and Wokwi simulation use different prefixes so Telegraf and the backend can tell them apart.

## Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `tekra/room/{room_id}/telemetry` | ESP32 → Server | Sensor data from real hardware |
| `tekra/room/{room_id}/commands` | Server → ESP32 | Actuator commands to real hardware |
| `tekra/wokwi/{room_id}/telemetry` | Wokwi → Server | Sensor data from simulation (dummy data) |
| `tekra/wokwi/{room_id}/commands` | Server → Wokwi | Commands to simulation |

## Wildcards Used by Subscribers

| Subscriber | Subscribes To | Why |
|------------|--------------|-----|
| Telegraf | `tekra/room/+/telemetry` | Store all real sensor data in QuestDB |
| Telegraf | `tekra/wokwi/+/telemetry` | Store all simulation data in QuestDB (separate tag) |
| FastAPI backend | `tekra/room/+/telemetry` | Run anomaly detection & override checks on real data |
| FastAPI backend | `tekra/wokwi/+/telemetry` | Optional: run same logic on simulation data for testing |

`+` is the single-level MQTT wildcard (matches exactly one segment, e.g. `A1.01`).

## Room ID Convention

Room IDs follow the format `{building_initial}{floor}.{room_number}`, e.g.:
- `A1.01` → Building A, Floor 1, Room 01
- `B2.03` → Building B, Floor 2, Room 03
