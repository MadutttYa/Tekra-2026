# Payload: Server → ESP32

Sent by the backend to the ESP32 whenever the room state needs to change — relay control, mode switch, or AC setpoint adjustment.

**MQTT Topic:** `tekra/room/{room_id}/commands`

## Example

```json
{
  "room_id": "A1.01",
  "timestamp": "2026-05-23T14:00:00Z",
  "mode": "AUTO",

  "actuators": {
    "master_relay": false,
    "lights": true,
    "ac": true,
    "outlets": true
  },

  "ac_setpoint": 24.0
}
```

## Field Reference

### Root

| Field | Type | Description |
|-------|------|-------------|
| `room_id` | string | Target room — ESP32 ignores messages not addressed to it |
| `timestamp` | string | ISO 8601 UTC timestamp of when the command was issued |
| `mode` | string | `"AUTO"` = system follows schedule; `"OVERRIDE"` = staff is in manual control |
| `ac_setpoint` | float | Target temperature in °C. Adjust setpoint rather than turning AC on/off to avoid energy spikes |

### `actuators`

| Field | Type | Description |
|-------|------|-------------|
| `master_relay` | bool | `true` = cut power to the entire room (emergency/fail-safe). Takes priority over all other fields |
| `lights` | bool | `true` = lights on |
| `ac` | bool | `true` = AC on |
| `outlets` | bool | `true` = wall outlets energized |

## Important Notes

- **`master_relay: true` overrides everything** — when set, the ESP32 must ignore all other actuator fields and cut all power immediately.
- The ESP32 must compare the received actuator states against its current relay states. If they differ without a command being sent, it must report a **physical override event** back to the server via the telemetry topic.
- The backend should only send this payload when something actually changes — avoid spamming the ESP32.
