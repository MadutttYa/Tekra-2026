# TEKRA Backend

FastAPI backend untuk sistem TEKRA. Menangani penerimaan data sensor via MQTT, penyimpanan ke dua database (QuestDB + SQLite), auto-control berbasis jadwal, deteksi anomali, dan distribusi data real-time ke dashboard via WebSocket.

## Database

### QuestDB (Port 8812 — PostgreSQL wire protocol)
Menyimpan seluruh data time-series sensor. Diakses via `asyncpg`.

Tabel utama: `room_telemetry`
- Diisi oleh **Telegraf** (bukan backend langsung)
- Backend hanya **membaca** untuk endpoint `/latest` dan `/history`
- Kolom: `room_id`, `source`, `temperature`, `humidity`, `heat_index`, `air_quality`, `lux`, `comfort_score`, `voltage`, `current`, `power_w`, `energy`, `frequency`, `pf`, `pir_triggered`, `estimated_people`, `activity_score`, `state`, `timestamp`

### SQLite (File: `tekra.db`)
Menyimpan semua data relasional yang dikelola backend:

| Tabel | Isi |
|-------|-----|
| `rooms` | Daftar ruangan, mode (AUTO/OVERRIDE/HOLIDAY), status |
| `schedules` | Jadwal kuliah berulang per ruangan (day_of_week, start_time, end_time) |
| `holidays` | Tanggal hari libur (format YYYY-MM-DD) |
| `bookings` | Peminjaman ruangan (PENDING/APPROVED/REJECTED) |
| `notifications` | Log anomali yang terdeteksi |

---

## Cara Menjalankan

```bash
cd backend/app
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Pastikan QuestDB dan Mosquitto sudah jalan (docker compose up -d dari root)

# Development (auto-reload):
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production:
PYTHONUNBUFFERED=1 nohup venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/tekra.log 2>&1 &
```

Cek kesehatan:
```bash
curl http://localhost:8000/health
# {"status":"ok","mqtt":true,"database":true}
```

Dokumentasi API interaktif: `http://localhost:8000/docs`

---

## Environment Variables

Konfigurasi via file `.env` di `backend/app/` (dibaca oleh `core/config.py`):

```env
APP_HOST=0.0.0.0
APP_PORT=8000

DB_HOST=localhost
DB_PORT=8812
DB_NAME=qdb
DB_USER=admin
DB_PASSWORD=quest

MQTT_HOST=localhost
MQTT_PORT=1883
```

---

## Alur Data

### Penerimaan Telemetry

```
ESP32 → MQTT Broker → mqtt/subscriber.py
                           │
                           ├─ broadcast() → WebSocket → Dashboard
                           ├─ check_and_notify() → anomaly.py → SQLite notifications
                           └─ apply_schedule_control() → auto_control.py → MQTT commands
```

`handle_message()` di `subscriber.py` memproses setiap pesan MQTT secara async. Koneksi ke broker dilakukan ulang otomatis jika terputus (loop `while True` dengan delay 5 detik).

### Auto-Control Berbasis Jadwal

Setiap kali telemetry masuk, `auto_control.py` memanggil `schedule_context.py` untuk mengevaluasi:

1. Apakah hari ini hari libur?
2. Apakah ada jadwal kuliah yang aktif sekarang?
3. Apakah ada peminjaman yang disetujui dan aktif sekarang?
4. Apakah kita dalam buffer 5 menit setelah jadwal berakhir?

Berdasarkan hasil dan kondisi hunian ruangan (`payload.occupancy.state`), backend menerbitkan command ke topik `tekra/room/{id}/commands` dan `tekra/wokwi/{id}/commands`.

**Logika keputusan:**

| Konteks waktu | Hunian | Tindakan |
|---------------|--------|----------|
| Hari libur | Apapun | AC off, lampu off |
| Dalam jadwal/booking | OCCUPIED / TRANSITIONING | AUTO (ESP32 memutuskan) |
| Dalam jadwal/booking | EMPTY | AC on (26°C), lampu off |
| Buffer 5 menit | TRANSITIONING | AC on |
| Buffer 5 menit | EMPTY | AC off |
| Tidak ada jadwal | EMPTY | AC off, lampu off |

Auto-control **hanya berlaku untuk ruangan ber-mode AUTO**. Ruangan OVERRIDE tidak disentuh.

### Evaluasi Waktu (WIB / UTC+7)

`schedule_context.py` selalu menggunakan waktu WIB:
```python
now = datetime.utcnow() + timedelta(hours=7)
```

Tidak ada ketergantungan terhadap timezone OS.

---

## Struktur Folder

```
app/
├── main.py                 Entry point: FastAPI app, lifespan, middleware, router registration
├── requirements.txt
├── core/
│   ├── config.py           Pydantic Settings, baca .env
│   ├── database.py         asyncpg pool helper, query QuestDB
│   └── sqlite.py           aiosqlite, init_db(), get_sqlite() dependency
├── api/
│   ├── rooms.py            GET/POST /rooms, PATCH mode, GET context
│   ├── sensors.py          GET /rooms/{id}/latest, /history
│   ├── schedules.py        GET/POST/DELETE /rooms/{id}/schedules
│   ├── holidays.py         GET/POST/DELETE /holidays
│   ├── bookings.py         GET/POST /rooms/{id}/bookings, PATCH/DELETE /bookings/{id}
│   ├── notifications.py    GET /notifications, PATCH acknowledge
│   ├── override.py         POST /rooms/{id}/command
│   └── ws.py               WebSocket /ws, ConnectionManager
├── mqtt/
│   └── subscriber.py       aiomqtt client, reconnect loop, handle_message()
├── models/
│   ├── sensor.py           SensorPayload (Pydantic)
│   ├── room.py             Room, RoomCreate, RoomModeUpdate
│   ├── schedule.py         Schedule, Holiday, Booking dan variannya
│   └── command.py          CommandPayload
└── services/
    ├── anomaly.py          check_and_notify(): 5 rule checks → insert notification + WS push
    ├── schedule_context.py get_room_context(): evaluasi jadwal aktif → dict context
    └── auto_control.py     apply_schedule_control(): kirim MQTT command berdasarkan context
```

---

## WebSocket Events

Klien terhubung ke `ws://localhost:8000/ws`. Semua event berbentuk JSON:

```json
{ "event": "<event_type>", "data": { ... } }
```

| Event | Dikirim saat | Data |
|-------|-------------|------|
| `sensor_update` | Telemetry baru masuk | room_id, source, environment, power, occupancy, timestamp |
| `new_notification` | Anomali terdeteksi | id, room_id, rule, message, severity, timestamp |

---

## Catatan Penting

- **Restart proses**: Jika backend di-restart sementara proses lama masih berjalan di port 8000, gunakan `kill $(lsof -t -i:8000)` sebelum start ulang.
- **SQLite migrasi**: `init_db()` menggunakan `CREATE TABLE IF NOT EXISTS` — tabel baru hanya dibuat saat startup. Jika menambah tabel baru ke `sqlite.py`, hapus `tekra.db` atau restart backend.
- **QuestDB hanya dibaca backend**: Penulisan data sensor ke QuestDB dilakukan oleh Telegraf, bukan backend.
