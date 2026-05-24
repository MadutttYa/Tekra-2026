# Intelligent Smart Classroom System for Real-Time Energy Monitoring and Environmental Safety

Sistem IoT untuk memantau kondisi ruang kelas secara real-time, mengotomasi manajemen energi berdasarkan jadwal kuliah, dan memberikan kontrol penuh kepada staf melalui dashboard terpusat.

---

## Arsitektur Sistem

![Arsitektur Sistem](Assets/Arsitektur%20Sistem.jpg)

```
ESP32 (sensor + relay)
    │  MQTT telemetry
    ▼
Mosquitto Broker ──────────────────────────┐
    │  MQTT subscribe                      │ MQTT subscribe
    ▼                                      ▼
Telegraf (json_v2 parser)           FastAPI Backend
    │  InfluxDB Line Protocol              │
    ▼                                      ├─ SQLite (rooms, schedules,
QuestDB (time-series)                      │         holidays, bookings,
    ▲                                      │         notifications)
    └──────── REST /history ───────────────┤
                                           ├─ WebSocket → Dashboard
                                           └─ REST API → Dashboard
```

---

## Solusi yang Ditawarkan

### 1. Monitoring Real-Time Multi-Ruangan
Setiap ruangan dipantau secara terus-menerus oleh ESP32 yang membaca 6 jenis sensor setiap 10 detik. Data dikirim via MQTT, disimpan di QuestDB untuk analisis historis, dan dipush ke dashboard via WebSocket tanpa polling.

### 2. Auto-Control Berbasis Jadwal Kuliah
Sistem membaca jadwal kuliah dan peminjaman ruangan, lalu secara otomatis menentukan status aktuator (AC dan lampu) berdasarkan konteks waktu real:

| Kondisi | Tindakan Otomatis |
|---------|-------------------|
| Dalam jam kuliah + ada orang | ESP32 AUTO (kontrol sendiri) |
| Dalam jam kuliah + kosong | AC tetap menyala (pre-cool 26°C), lampu mati |
| Buffer 5 menit pasca kelas + masih ada orang | AC tetap menyala |
| Tidak ada jadwal + kosong | AC dan lampu mati |
| Hari libur | Semua aktuator mati, kehadiran memicu alert CRITICAL |

**Alur keputusan** berjalan setiap kali data telemetry masuk dari ESP32, menjamin respons dalam hitungan detik.

### 3. Manajemen Jadwal & Peminjaman Ruangan
- **Jadwal Kuliah**: Staf dapat mendaftarkan jadwal ruangan berulang (per hari dalam seminggu) via dashboard.
- **Peminjaman Ruangan**: Pengguna dapat mengajukan peminjaman untuk tanggal dan jam tertentu. Admin menyetujui atau menolak via dashboard. Peminjaman yang disetujui berlaku setara dengan jadwal kuliah dalam konteks auto-control.
- **Hari Libur**: Admin mendaftarkan tanggal libur (nasional/kampus). Pada hari libur, auto-control menonaktifkan seluruh sistem dan setiap kehadiran yang terdeteksi memicu notifikasi CRITICAL.

### 4. Deteksi Anomali Otomatis
Rule engine yang berjalan pada setiap data masuk:

| Rule | Kondisi | Severity |
|------|---------|----------|
| `HIGH_TEMP` | Suhu > 35°C | WARNING |
| `POWER_SPIKE` | Daya > 3000W | WARNING |
| `BAD_AIR` | CO₂ > 1000 ppm | WARNING |
| `LOW_COMFORT` | Comfort score < 30 | WARNING |
| `UNEXPECTED_PRESENCE` | Ruangan HOLIDAY tapi terdeteksi orang | CRITICAL |

Anomali tidak memicu tindakan otomatis — semua aksi tetap dikonfirmasi staf.

### 5. Solusi BH1750 & Feedback Loop Cahaya
Sensor cahaya BH1750 pada perangkat nyata berpotensi mengalami feedback loop: lampu menyala → lux tinggi → lampu mati → lux rendah → lampu menyala lagi. Solusi yang diterapkan:

- **Dual-threshold hysteresis**: Lampu ON jika lux < 200, OFF jika lux > 700. Tidak ada toggle di rentang 200–700.
- **State lock 5 menit**: Setelah keputusan dibuat, sistem menunggu 5 menit sebelum mengevaluasi ulang.
- **Wokwi**: Simulasi menggunakan lux yang disintesis secara random, sehingga tidak mengalami feedback loop. Deteksi anomali dinonaktifkan untuk sumber Wokwi.

### 6. Dashboard Glassmorphism Terpadu
Single-file dashboard (`dashboard/index.html`) dengan 5 seksi:

| Seksi | Isi |
|-------|-----|
| **Dasbor Utama** | Statistik agregat (rata-rata daya, kenyamanan), kalender interaktif, notifikasi, form peminjaman cepat |
| **Tampilan Detail** | Grid kartu semua ruangan, klik → panel detail dengan 6 metrik + 3 grafik historis + panel kontrol penuh |
| **Jadwal Kuliah** | Lihat jadwal mingguan per ruangan, tambah slot jadwal baru |
| **Peminjaman** | Ajukan peminjaman, approve/reject pending, lihat semua booking |
| **Hari Libur** | Daftar libur, tambah, hapus |

---

## Komponen Utama

### Firmware ESP32
Setiap ruangan dipasang satu ESP32 yang menjalankan FreeRTOS dengan dua task utama:

| Task | Fungsi |
|------|--------|
| `taskReadSensors` | Baca semua sensor setiap 10 detik, hitung comfort score, kontrol relay |
| `taskMQTT` | Koneksi broker, publish telemetry, subscribe command |

**Sensor:**
- **DHT22 × 2** — suhu & kelembaban (sensor fusion: rata-rata dua sensor)
- **PIR × 2** — deteksi kehadiran (estimasi jumlah orang)
- **Gas Sensor × 2** — kualitas udara / CO₂ (analog ADC)
- **Potentiometer** — simulasi konsumsi daya (0–15A)

**Pin Relay:**
| Relay | Pin | Fungsi |
|-------|-----|--------|
| Master | 17 | Emergency cutoff; HIGH memutus jalur power ke relay lampu dan AC via NC |
| Lampu | 21 | Kontrol pencahayaan |
| AC | 23 | Kontrol pendingin |

**Payload telemetry (ESP32 → Server):**
```json
{
  "device_id": "ESP-SIM-1",
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:00:00Z",
  "environment": {
    "temperature": 26.8, "humidity": 64.0, "heat_index": 28.1,
    "air_quality": 620, "lux": 412, "comfort_score": 78.5
  },
  "power": {
    "voltage": 220.0, "current": 4.2, "power": 879.0,
    "energy": 0.073, "frequency": 50.0, "pf": 0.95
  },
  "occupancy": {
    "pir_triggered": true, "estimated_people": 22,
    "activity_score": 1.0, "state": "OCCUPIED"
  }
}
```

**Payload command (Server → ESP32):**
```json
{
  "actuators": { "master_relay": false, "lights": true, "ac": true },
  "ac_setpoint": 26.0
}
```

---

### Mosquitto MQTT Broker

**Skema topik:**
```
tekra/room/{room_id}/telemetry   ← data sensor real dari hardware
tekra/room/{room_id}/commands    → perintah kontrol ke hardware
tekra/wokwi/{room_id}/telemetry  ← data sensor dari simulasi Wokwi
tekra/wokwi/{room_id}/commands   → perintah kontrol ke simulasi
```

Prefix `wokwi` memisahkan data simulasi sehingga anomaly detection tidak terpicu oleh noise simulasi.

---

### Telegraf (Pipeline Data)

```
MQTT Broker → Telegraf (mqtt_consumer + json_v2) → QuestDB (port 9009)
```

Setiap pesan JSON dari ESP32 menjadi satu baris `room_telemetry` di QuestDB, dengan tag `room_id` dan `source` yang diekstrak dari nama topik.

---

### FastAPI Backend

**Dua Database:**
| Database | Digunakan untuk |
|----------|----------------|
| **QuestDB** | Data time-series sensor (grafik historis, query rentang waktu) |
| **SQLite** | Data relasional: rooms, schedules, holidays, bookings, notifications |

**REST API Lengkap:**
```
GET    /rooms                                Daftar semua ruangan
POST   /rooms                                Daftarkan ruangan baru
GET    /rooms/{id}                           Detail ruangan
PATCH  /rooms/{id}/mode                      Ganti mode: AUTO/OVERRIDE/HOLIDAY
GET    /rooms/{id}/context                   Status jadwal aktif saat ini
GET    /rooms/{id}/latest                    Data sensor terbaru
GET    /rooms/{id}/history                   Riwayat sensor (time range)
GET    /rooms/{id}/schedules                 Jadwal ruangan
POST   /rooms/{id}/schedules                 Tambah jadwal
DELETE /schedules/{id}                       Hapus jadwal
GET    /rooms/{id}/bookings                  Peminjaman ruangan
POST   /rooms/{id}/bookings                  Ajukan peminjaman
GET    /bookings                             Semua peminjaman (admin)
PATCH  /bookings/{id}/status                 Approve/reject peminjaman
DELETE /bookings/{id}                        Hapus peminjaman
GET    /holidays                             Daftar hari libur
POST   /holidays                             Tambah hari libur
DELETE /holidays/{id}                        Hapus hari libur
POST   /rooms/{id}/command                   Kirim command aktuator (OVERRIDE only)
GET    /notifications                        Daftar notifikasi anomali
PATCH  /notifications/{id}/acknowledge       Tandai sudah dibaca
WS     /ws                                   WebSocket real-time feed
GET    /health                               Status backend, MQTT, database
```

**Mode Operasi Ruangan:**
| Mode | Perilaku |
|------|----------|
| `AUTO` | Sistem mengikuti jadwal. Auto-control aktif. |
| `OVERRIDE` | Staf kontrol manual via API. Auto-control diabaikan. |
| `HOLIDAY` | Sistem mati total. Kehadiran → CRITICAL alert. |

---

### Simulasi Wokwi

Dua simulasi ESP32 berjalan paralel untuk dua ruangan:

| Simulasi | Room ID | Device ID | Topik |
|----------|---------|-----------|-------|
| ESP_1_test | A1.01 | ESP-SIM-1 | tekra/wokwi/A1.01/+ |
| ESP_2_test | A1.02 | ESP-SIM-2 | tekra/wokwi/A1.02/+ |

---

## Cara Menjalankan

### Prasyarat
- Docker & Docker Compose
- Python 3.12+
- PlatformIO (untuk firmware/simulasi)
- Wokwi VS Code Extension

### 1. Jalankan infrastruktur
```bash
docker compose up -d
# Mosquitto :1883, QuestDB :8812/:9009, Telegraf
```

### 2. Jalankan Backend
```bash
cd backend/app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
PYTHONUNBUFFERED=1 venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# Atau untuk pengembangan (auto-reload):
# venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Jalankan Simulasi Wokwi
```bash
cd Simulation/ESP_1_test && pio run   # build ESP 1
cd Simulation/ESP_2_test && pio run   # build ESP 2
# Buka VS Code → Wokwi: Start Simulator (untuk masing-masing)
```

### 4. Buka Dashboard
```bash
# Buka di browser:
xdg-open dashboard/index.html
# atau
firefox dashboard/index.html
```

### 5. Cek kesehatan sistem
```bash
curl http://localhost:8000/health
# {"status":"ok","mqtt":true,"database":true}
```

### 6. Test pipeline MQTT manual
```bash
mosquitto_pub -h localhost -t "tekra/wokwi/A1.01/telemetry" -f shared/payload_esp_to_server.json
```

---

## Struktur Direktori

```
lomba/
├── docker-compose.yml          Mosquitto + QuestDB + Telegraf
├── mosquitto/mosquitto.conf
├── telegraf/telegraf.conf
├── backend/
│   └── app/
│       ├── main.py             FastAPI app + lifespan
│       ├── core/
│       │   ├── config.py       Settings dari .env
│       │   ├── database.py     QuestDB queries
│       │   └── sqlite.py       SQLite schema + helper
│       ├── api/
│       │   ├── rooms.py        CRUD ruangan + mode + context
│       │   ├── sensors.py      Query data sensor
│       │   ├── schedules.py    Jadwal ruangan
│       │   ├── holidays.py     Hari libur
│       │   ├── bookings.py     Peminjaman ruangan
│       │   ├── notifications.py Notifikasi anomali
│       │   ├── override.py     Command aktuator
│       │   └── ws.py           WebSocket endpoint
│       ├── mqtt/
│       │   └── subscriber.py   MQTT listener + reconnect + dispatch
│       ├── models/
│       │   ├── sensor.py       Schema payload ESP32
│       │   ├── room.py         Schema ruangan
│       │   ├── schedule.py     Schema jadwal, holiday, booking
│       │   └── command.py      Schema command aktuator
│       └── services/
│           ├── anomaly.py      Rule engine deteksi anomali
│           ├── schedule_context.py  Evaluasi jadwal aktif (WIB)
│           └── auto_control.py     Kirim command berbasis jadwal
├── dashboard/
│   └── index.html              Single-file dashboard (HTML+CSS+JS)
├── Simulation/
│   ├── ESP_1_test/             Wokwi sim → room A1.01
│   └── ESP_2_test/             Wokwi sim → room A1.02
└── shared/
    ├── mqtt_topics.md
    ├── payload_esp_to_server.json
    └── payload_server_to_esp.json
```
