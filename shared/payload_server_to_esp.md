# Payload: Server → ESP32 (Command)

Dikirim oleh backend ke ESP32 melalui broker MQTT ketika:
- Auto-control menentukan perlu mengubah kondisi aktuator berdasarkan jadwal
- Staf mengirim perintah manual melalui dashboard (mode OVERRIDE)
- Mode ruangan berubah (AUTO ↔ OVERRIDE ↔ HOLIDAY)
- Master relay diaktifkan/dinonaktifkan

**Topik MQTT:** `tekra/room/{room_id}/commands`

---

## Contoh

### OVERRIDE — Lampu dan AC menyala
```json
{
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:15:00Z",
  "mode": "OVERRIDE",
  "actuators": {
    "master_relay": false,
    "lights": true,
    "ac": true
  },
  "ac_setpoint": 24.0
}
```

### AUTO — Kembalikan kontrol ke ESP32
```json
{
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:15:00Z",
  "mode": "AUTO"
}
```

### EMERGENCY — Putus seluruh daya ruangan
```json
{
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:15:00Z",
  "mode": "OVERRIDE",
  "actuators": {
    "master_relay": true,
    "lights": false,
    "ac": false
  },
  "ac_setpoint": 24.0
}
```

### Pre-conditioning (Auto-Control, jadwal aktif + ruangan kosong)
```json
{
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:15:00Z",
  "mode": "OVERRIDE",
  "actuators": {
    "master_relay": false,
    "lights": false,
    "ac": true
  },
  "ac_setpoint": 26.0
}
```

---

## Referensi Field

### Root

| Field | Tipe | Keterangan |
|-------|------|------------|
| `room_id` | string | Ruangan target. ESP32 mengabaikan command yang bukan miliknya. |
| `timestamp` | string | Waktu command diterbitkan (ISO 8601 UTC), ditambahkan otomatis oleh backend |
| `mode` | string | `AUTO` = ESP32 kontrol sendiri · `OVERRIDE` = ikuti field `actuators` |
| `ac_setpoint` | float | Target suhu AC dalam °C (default 24.0). Hanya berlaku saat `ac: true` |

### `actuators`

| Field | Tipe | Keterangan |
|-------|------|------------|
| `master_relay` | bool | `true` = putus seluruh arus ruangan (emergency cutoff). **Mengalahkan semua field lain.** |
| `lights` | bool | `true` = lampu menyala. Hanya diproses saat `mode: OVERRIDE` |
| `ac` | bool | `true` = AC menyala. Hanya diproses saat `mode: OVERRIDE` |

---

## Aturan Prioritas (di ESP32)

```
1. master_relay = true  →  semua relay OFF, abaikan semua field lain
2. mode = "OVERRIDE"    →  terapkan lights dan ac dari actuators
3. mode = "AUTO"        →  ESP32 memutuskan sendiri berdasarkan sensor:
                            • Lampu ON  jika lux < 300
                            • AC    ON  jika OCCUPIED/TRANSITIONING
                                        ATAU suhu ≥ 28°C
                                        ATAU CO₂ ≥ 900 ppm
```

---

## Kapan Backend Mengirim Command

| Pemicu | Siapa yang kirim | Isi |
|--------|-----------------|-----|
| Telemetry masuk + jadwal aktif + ruangan KOSONG | Auto-Control (`auto_control.py`) | OVERRIDE, AC on (pre-cool 26°C), lights off |
| Telemetry masuk + jadwal aktif + ada orang | Auto-Control | AUTO |
| Telemetry masuk + tidak ada jadwal + EMPTY | Auto-Control | OVERRIDE, semua off |
| Staf klik tombol di dashboard | REST `POST /rooms/{id}/command` | sesuai input staf |
| Staf aktifkan master relay | REST `POST /rooms/{id}/command` | master_relay: true |
| Staf ganti mode ruangan | `PATCH /rooms/{id}/mode` + command | mode baru |
