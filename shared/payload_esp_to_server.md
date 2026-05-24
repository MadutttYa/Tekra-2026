# Payload: ESP32 → Server

Sent by the ESP32 periodically (or on significant sensor change) to the backend via MQTT.

**MQTT Topic:** `tekra/room/{room_id}/telemetry`
**Wokwi simulation topic:** `tekra/wokwi/{room_id}/telemetry`

## Example

```json
{
  "device_id": "ESP-1",
  "building_id": "Gedung-A",
  "floor": 1,
  "room_id": "A1.01",
  "timestamp": "2026-05-23T14:00:00Z",

  "environment": {
    "temperature": 0.0,
    "humidity": 0.0,
    "heat_index": 0.0,
    "air_quality": 0.0,
    "lux": 0.0,
    "comfort_score": 0.0
  },

  "power": {
    "voltage": 0.0,
    "current": 0.0,
    "power": 0.0,
    "energy": 0.0,
    "frequency": 0.0,
    "pf": 0.0
  },

  "occupancy": {
    "pir_triggered": false,
    "estimated_people": 0,
    "activity_score": 0.0,
    "state": "EMPTY"
  }
}
```

## Field Reference

### Root

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | string | Unique ID of the ESP32 unit |
| `building_id` | string | Building where the room is located |
| `floor` | int | Floor number |
| `room_id` | string | Room identifier, e.g. `"A1.01"` |
| `timestamp` | string | ISO 8601 UTC timestamp of when data was captured |

### `environment`

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `temperature` | float | °C | Ambient temperature |
| `humidity` | float | % | Relative humidity |
| `heat_index` | float | °C | Perceived temperature (temperature + humidity combined) |
| `air_quality` | float | ppm | CO₂ or VOC air quality reading |
| `lux` | float | lux | Ambient light level |
| `comfort_score` | float | 0–100 | Comfort index computed on the ESP32 (fused from temp, humidity, air quality, lux) |

### `power`

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `voltage` | float | V | Supply voltage |
| `current` | float | A | Current draw |
| `power` | float | W | Active power consumption |
| `energy` | float | kWh | Cumulative energy consumed (resets on ESP32 restart) |
| `frequency` | float | Hz | AC frequency |
| `pf` | float | 0–1 | Power factor |

### `occupancy`

| Field | Type | Description |
|-------|------|-------------|
| `pir_triggered` | bool | Whether the PIR sensor is currently detecting motion |
| `estimated_people` | int | Estimated number of people in the room (sensor fusion result) |
| `activity_score` | float | 0–1 activity level derived from sensor fusion |
| `state` | string | One of: `"EMPTY"`, `"OCCUPIED"`, `"TRANSITIONING"` |
