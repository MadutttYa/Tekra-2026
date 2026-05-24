# shared — Kontrak & Referensi Bersama

Folder ini berisi dokumen kontrak yang digunakan bersama oleh firmware ESP32, backend, dan Telegraf. Semua pihak yang berkomunikasi via MQTT harus mengikuti format di sini.

---

## File

| File | Isi |
|------|-----|
| `mqtt_topics.md` | Skema topik MQTT lengkap dengan wildcard dan konvensi Room ID |
| `payload_esp_to_server.json` | Contoh payload telemetry dari ESP32 ke server (format JSON) |
| `payload_esp_to_server.md` | Dokumentasi field-field payload telemetry |
| `payload_server_to_esp.json` | Contoh payload command dari server ke ESP32 |
| `payload_server_to_esp.md` | Dokumentasi field-field payload command |

---

## Topik MQTT

```
tekra/room/{room_id}/telemetry    ESP32 real → Broker → Backend & Telegraf
tekra/room/{room_id}/commands     Backend → Broker → ESP32 real
tekra/wokwi/{room_id}/telemetry   Wokwi sim → Broker → Backend & Telegraf
tekra/wokwi/{room_id}/commands    Backend → Broker → Wokwi sim
```

Prefix `room` vs `wokwi` memungkinkan backend membedakan sumber data. Anomaly detection hanya dijalankan untuk sumber `room`.

**Konvensi Room ID**: `{inisial_gedung}{lantai}.{nomor_ruang}` — contoh: `A1.01`, `B2.03`

---

## Payload Telemetry (ESP32 → Server)

```json
{
  "device_id": "ESP-REAL-1",
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:00:00Z",
  "environment": {
    "temperature": 26.8,      // °C
    "humidity": 64.0,         // %RH
    "heat_index": 28.1,       // °C (dihitung dari suhu + kelembaban)
    "air_quality": 620,       // ppm CO₂ estimasi
    "lux": 412,               // lux
    "comfort_score": 78.5     // 0-100 (weighted: suhu 35%, RH 25%, CO₂ 25%, lux 15%)
  },
  "power": {
    "voltage": 220.0,         // Volt
    "current": 4.2,           // Ampere
    "power": 879.0,           // Watt (V × I × PF)
    "energy": 0.073,          // kWh (akumulasi sejak boot)
    "frequency": 50.0,        // Hz
    "pf": 0.95                // Power factor
  },
  "occupancy": {
    "pir_triggered": true,    // true jika salah satu PIR aktif
    "estimated_people": 22,   // estimasi jumlah orang
    "activity_score": 1.0,    // 0.0-1.0 (rasio PIR aktif)
    "state": "OCCUPIED"       // EMPTY | TRANSITIONING | OCCUPIED
  }
}
```

---

## Payload Command (Server → ESP32)

```json
{
  "mode": "OVERRIDE",
  "actuators": {
    "master_relay": false,   // true = matikan semua (emergency)
    "lights": true,          // true = lampu ON
    "ac": true               // true = AC ON
  },
  "ac_setpoint": 26.0        // target suhu AC (°C)
}
```

- `"mode": "AUTO"` → ESP32 memutuskan sendiri berdasarkan sensor; field `actuators` diabaikan
- `"mode": "OVERRIDE"` → ESP32 mengikuti field `actuators`
- `master_relay: true` → semua relay dimatikan paksa tanpa memandang mode

---

## Test Cepat Pipeline

```bash
# Kirim satu telemetry manual ke topik Wokwi (tidak trigger anomali):
mosquitto_pub -h localhost -t "tekra/wokwi/A1.01/telemetry" \
  -f shared/payload_esp_to_server.json

# Kirim ke topik real (AKAN trigger anomaly check):
mosquitto_pub -h localhost -t "tekra/room/A1.01/telemetry" \
  -f shared/payload_esp_to_server.json

# Kirim command ke simulasi:
mosquitto_pub -h localhost -t "tekra/wokwi/A1.01/commands" \
  -f shared/payload_server_to_esp.json
```
