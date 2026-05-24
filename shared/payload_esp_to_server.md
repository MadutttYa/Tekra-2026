# Payload: ESP32 → Server (Telemetry)

Dikirim oleh ESP32 ke broker MQTT setiap **10 detik**.  
Backend menerima, memvalidasi, lalu meneruskan ke dashboard via WebSocket.  
Telegraf secara terpisah menyimpan data ini ke QuestDB untuk riwayat historis.

**Topik MQTT:** `tekra/room/{room_id}/telemetry`

---

## Contoh

```json
{
  "device_id": "ESP-A1.01",
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:15:00Z",

  "environment": {
    "temperature": 27.4,
    "humidity": 65.0,
    "heat_index": 29.2,
    "air_quality": 712,
    "lux": 380.0,
    "comfort_score": 72.5
  },

  "power": {
    "voltage": 220.0,
    "current": 4.8,
    "power": 1003.0,
    "energy": 0.167,
    "frequency": 50.0,
    "pf": 0.95
  },

  "occupancy": {
    "pir_triggered": true,
    "estimated_people": 24,
    "activity_score": 1.0,
    "state": "OCCUPIED"
  }
}
```

---

## Referensi Field

### Root

| Field | Tipe | Keterangan |
|-------|------|------------|
| `device_id` | string | ID unik unit ESP32, format `ESP-{room_id}` |
| `room_id` | string | Identitas ruangan, format `{Gedung}{Lantai}.{Nomor}` — contoh `A1.01` |
| `timestamp` | string | Waktu pembacaan sensor dalam format ISO 8601 UTC |

### `environment`

| Field | Tipe | Satuan | Keterangan |
|-------|------|--------|------------|
| `temperature` | float | °C | Suhu udara (rata-rata dua sensor DHT22) |
| `humidity` | float | % | Kelembaban relatif (rata-rata dua sensor DHT22) |
| `heat_index` | float | °C | Suhu terasa (*heat index*), dihitung dari suhu + kelembaban |
| `air_quality` | float | ppm | Estimasi konsentrasi CO₂ / VOC dari sensor gas (ADC) |
| `lux` | float | lux | Intensitas cahaya dari sensor BH1750 |
| `comfort_score` | float | 0–100 | Skor kenyamanan ruangan — dihitung di ESP32 dari fusi keempat sensor |

**Formula comfort score** (dihitung ESP32):
```
tempScore = 100 - |temp - 22.5| × 6        (bobot 35%)
humScore  = 100 - |hum - 50| × 2           (bobot 25%)
airScore  = map(ppm, 400→1500, 100→0)      (bobot 25%)
luxScore  = 100 jika 200 ≤ lux ≤ 600, 50 selainnya  (bobot 15%)
```

### `power`

| Field | Tipe | Satuan | Keterangan |
|-------|------|--------|------------|
| `voltage` | float | V | Tegangan sumber (PLN ~220V) |
| `current` | float | A | Arus total ruangan (0–15A) |
| `power` | float | W | Daya aktif (`voltage × current × pf`) |
| `energy` | float | kWh | Energi kumulatif sejak ESP32 menyala (reset saat restart) |
| `frequency` | float | Hz | Frekuensi jaringan PLN (50 Hz) |
| `pf` | float | 0–1 | Power factor |

> **Catatan:** Field `power` dalam JSON ini berisi watt. Saat disimpan ke QuestDB oleh Telegraf, field ini diubah namanya menjadi `power_w` untuk menghindari konflik dengan nama pengukuran.

### `occupancy`

| Field | Tipe | Keterangan |
|-------|------|------------|
| `pir_triggered` | bool | `true` jika salah satu atau kedua sensor PIR aktif saat pembacaan |
| `estimated_people` | int | Estimasi jumlah orang berdasarkan sensor fusion PIR |
| `activity_score` | float | Rasio PIR aktif: `0.0` (kosong) · `0.5` (satu PIR) · `1.0` (dua PIR) |
| `state` | string | Status hunian: `EMPTY` · `TRANSITIONING` · `OCCUPIED` |

**Logika penentuan state:**

| PIR 1 | PIR 2 | State | Estimasi Orang |
|-------|-------|-------|----------------|
| ❌ | ❌ | `EMPTY` | 0 |
| ✅ | ❌ atau ❌ ✅ | `TRANSITIONING` | 1–10 |
| ✅ | ✅ | `OCCUPIED` | 15–35 |
