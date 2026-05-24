# TEKRA — Sistem Monitoring & Kontrol Ruang Kelas Pintar

TEKRA (*Teknologi Ruang Kelas Adaptif*) adalah sistem IoT untuk memantau kondisi ruang kelas secara real-time, mengotomasi manajemen energi, dan memberikan kontrol penuh kepada staf melalui dashboard terpusat.

---

## Arsitektur Sistem

![Arsitektur Sistem](Assets/Arsitektur%20Sistem.jpg)

---

## Komponen Utama

### 1. Firmware ESP32
Setiap ruangan dipasang satu ESP32 yang menjalankan FreeRTOS dengan dua task utama:

| Task | Fungsi |
|------|--------|
| `taskReadSensors` | Baca semua sensor setiap 10 detik, hitung comfort score, kontrol relay otomatis |
| `taskMQTT` | Koneksi ke broker, publish telemetry, subscribe command |

**Sensor yang digunakan:**
- **DHT22 x2** — suhu & kelembaban (sensor fusion: rata-rata dua sensor)
- **PIR x2** — deteksi kehadiran (sensor fusion: estimasi jumlah orang)
- **Gas Sensor x2** — kualitas udara / CO₂ (analog ADC)
- **Potentiometer** — simulasi konsumsi daya (0–15A)

**Relay yang dikontrol:**
- **Relay Master (pin 17)** — emergency cutoff seluruh ruangan. Saat aktif (HIGH), memutus jalur power ke relay lampu dan AC melalui kontak NC
- **Relay Lampu (pin 21)** — kontrol pencahayaan
- **Relay AC (pin 23)** — kontrol pendingin ruangan

**Payload telemetry (ESP32 → Server):**
```json
{
  "device_id": "ESP-REAL-1",
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:00:00Z",
  "environment": {
    "temperature": 26.8,
    "humidity": 64.0,
    "heat_index": 28.1,
    "air_quality": 620,
    "lux": 412,
    "comfort_score": 78.5
  },
  "power": {
    "voltage": 220.0,
    "current": 4.2,
    "power": 879.0,
    "energy": 0.073,
    "frequency": 50.0,
    "pf": 0.95
  },
  "occupancy": {
    "pir_triggered": true,
    "estimated_people": 22,
    "activity_score": 1.0,
    "state": "OCCUPIED"
  }
}
```

**Payload command (Server → ESP32):**
```json
{
  "actuators": {
    "master_relay": false,
    "lights": true,
    "ac": true
  },
  "ac_setpoint": 22.0
}
```

---

### 2. Mosquitto MQTT Broker

Broker sentral yang meneruskan pesan antara ESP32 dan backend.

**Skema topik:**
```
tekra/room/{room_id}/telemetry   ← data sensor real dari hardware
tekra/room/{room_id}/commands    → perintah kontrol ke hardware
tekra/wokwi/{room_id}/telemetry  ← data sensor dari simulasi Wokwi
tekra/wokwi/{room_id}/commands   → perintah kontrol ke simulasi
```

Prefix `wokwi` digunakan agar data simulasi tidak memicu anomaly detection di backend.

---

### 3. Telegraf (Pipeline Data)

Telegraf berperan sebagai jembatan antara MQTT broker dan QuestDB menggunakan plugin `mqtt_consumer` dengan parser `json_v2`.

```
MQTT Broker → Telegraf (json_v2 parser) → QuestDB (InfluxDB Line Protocol, port 9009)
```

Setiap pesan JSON dari ESP32 diurai menjadi satu baris `room_telemetry` di QuestDB, termasuk tag `room_id` dan `source` (room/wokwi) yang diekstrak dari nama topik.

---

### 4. FastAPI Backend

Backend async yang menangani tiga tanggung jawab utama:

**a. MQTT Subscriber**
- Berjalan sebagai background task asyncio
- Subscribe ke semua topik telemetry
- Melakukan reconnect otomatis jika koneksi ke broker terputus
- Broadcast data real-time ke dashboard via WebSocket
- Jalankan anomaly detection (hanya untuk data real, bukan Wokwi)

**b. Anomaly Detection**
Aturan deteksi anomali yang aktif berjalan setiap kali data masuk:

| Rule | Kondisi | Severity |
|------|---------|----------|
| `HIGH_TEMP` | Suhu > 35°C | WARNING |
| `POWER_SPIKE` | Daya > 3000W | WARNING |
| `BAD_AIR` | CO₂ > 1000 ppm | WARNING |
| `LOW_COMFORT` | Comfort score < 30 | WARNING |
| `UNEXPECTED_PRESENCE` | Ruangan HOLIDAY tapi terdeteksi orang | CRITICAL |

Anomali disimpan ke SQLite dan di-push ke dashboard via WebSocket. Sistem **tidak mengambil tindakan otomatis** — staf harus konfirmasi terlebih dahulu.

**c. REST API**
```
GET    /rooms                          Daftar semua ruangan
GET    /rooms/{room_id}/latest         Data sensor terbaru
GET    /rooms/{room_id}/history        Riwayat sensor (time range)
PATCH  /rooms/{room_id}/mode           Ganti mode: AUTO / OVERRIDE / HOLIDAY
POST   /rooms/{room_id}/command        Kirim perintah aktuator (hanya mode OVERRIDE)
GET    /notifications                  Daftar notifikasi anomali
PATCH  /notifications/{id}/acknowledge Tandai notifikasi sudah dibaca
GET    /rooms/{room_id}/schedules      Jadwal ruangan
POST   /rooms/{room_id}/schedules      Tambah jadwal
WS     /ws                             WebSocket real-time feed
```

**d. Dua Database**
| Database | Digunakan untuk |
|----------|----------------|
| **QuestDB** | Data time-series sensor (query historis, grafik) |
| **SQLite** | Data relasional: rooms, schedules, notifications |

---

### 5. Mode Operasi Ruangan

| Mode | Perilaku |
|------|----------|
| `AUTO` | Sistem mengikuti jadwal ruangan. Command aktuator ditolak (409). |
| `OVERRIDE` | Staf dapat mengontrol aktuator secara manual via API. |
| `HOLIDAY` | Ruangan tidak aktif. Kehadiran yang terdeteksi memicu notifikasi CRITICAL. |

---

### 6. Simulasi Wokwi

Untuk keperluan pengembangan dan demonstrasi, ESP32 dapat disimulasikan menggunakan Wokwi + PlatformIO tanpa hardware fisik.

```
Simulation/ESP_1_test/
├── src/main.cpp        Firmware ESP32 (FreeRTOS)
├── diagram.json        Skema rangkaian elektronik
├── platformio.ini      Konfigurasi build
└── wokwi.toml          Mapping firmware ke simulator
```

Simulasi terhubung ke broker MQTT yang sama via WiFi `Wokwi-GUEST` dan mempublish ke topik `tekra/wokwi/+/telemetry`.

---

## Cara Menjalankan

### Prasyarat
- Docker & Docker Compose
- Python 3.12+
- PlatformIO (untuk firmware/simulasi)
- Wokwi VS Code Extension (untuk simulasi)
- `mosquitto-clients` (`sudo apt install mosquitto-clients`)

### 1. Jalankan infrastruktur (Broker + Database)
```bash
docker compose up -d
```

### 2. Jalankan Backend
```bash
cd backend/app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
PYTHONUNBUFFERED=1 venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Jalankan Simulasi Wokwi
```bash
cd Simulation/ESP_1_test
pio run                  # build firmware
# Buka VS Code → Wokwi: Start Simulator
```

### 4. Test Pipeline MQTT
```bash
# Kirim data normal (topik Wokwi, tidak trigger anomali)
./shared/test_payload.sh

# Kirim data anomali (topik real, trigger notifikasi)
./shared/test_payload.sh anomaly
```

### 5. Cek kesehatan sistem
```bash
curl http://localhost:8000/health
# {"status":"ok","mqtt":true,"database":true}
```

---

## Struktur Direktori

```
tekra/
├── docker-compose.yml          Mosquitto + QuestDB + Telegraf
├── mosquitto/
│   └── mosquitto.conf
├── telegraf/
│   └── telegraf.conf
├── backend/
│   └── app/
│       ├── main.py             FastAPI app + lifespan
│       ├── core/
│       │   ├── config.py       Settings dari .env
│       │   ├── database.py     QuestDB queries
│       │   └── sqlite.py       SQLite schema + helpers
│       ├── api/
│       │   ├── rooms.py        CRUD ruangan + mode
│       │   ├── sensors.py      Query data sensor
│       │   ├── schedules.py    Jadwal ruangan
│       │   ├── notifications.py Notifikasi anomali
│       │   ├── override.py     Kirim command aktuator
│       │   └── ws.py           WebSocket endpoint
│       ├── mqtt/
│       │   ├── subscriber.py   MQTT listener + reconnect
│       │   └── publisher.py    Kirim command ke ESP32
│       ├── models/
│       │   ├── sensor.py       Schema payload ESP32
│       │   ├── room.py         Schema ruangan
│       │   └── command.py      Schema command aktuator
│       └── services/
│           └── anomaly.py      Rule engine deteksi anomali
├── Simulation/
│   └── ESP_1_test/             Proyek Wokwi + PlatformIO
└── shared/
    ├── mqtt_topics.md          Kontrak topik MQTT
    ├── payload_esp_to_server.json
    ├── payload_server_to_esp.json
    └── test_payload.sh         Script test pipeline MQTT
```
