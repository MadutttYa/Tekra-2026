# ESP_1_test — Simulasi ESP32 Wokwi (Ruangan A1.01)

Proyek PlatformIO + Wokwi yang mensimulasikan satu unit ESP32 untuk ruangan **A1.01 (Gedung-A, Lantai 1)**. Firmware identik dengan hardware nyata — terhubung ke broker MQTT yang sama dan mempublish data telemetry setiap 10 detik.

---

## Identitas Perangkat

| Parameter | Nilai |
|-----------|-------|
| Room ID | `A1.01` |
| Device ID | `ESP-SIM-1` |
| Building | `Gedung-A` |
| Floor | `1` |
| Topik telemetry | `tekra/wokwi/A1.01/telemetry` |
| Topik command | `tekra/wokwi/A1.01/commands` |

---

## Cara Menjalankan

### Prasyarat
- PlatformIO (`pip install platformio` atau ekstensi VS Code)
- Wokwi VS Code Extension
- Broker MQTT jalan di IP yang dikonfigurasi (`MQTT_BROKER` di `main.cpp`)

### Build & Simulasi
```bash
cd Simulation/ESP_1_test
pio run                      # compile firmware → .pio/build/esp32dev/firmware.bin
```

Buka folder di VS Code, lalu jalankan **Wokwi: Start Simulator**. Simulator akan menggunakan `diagram.json` sebagai skema rangkaian dan `wokwi.toml` sebagai mapping firmware.

---

## Konfigurasi Jaringan

```cpp
#define WIFI_SSID    "Wokwi-GUEST"   // Built-in Wokwi WiFi, tidak perlu password
#define WIFI_PASSWORD ""
#define MQTT_BROKER  "10.200.64.195"  // Ganti dengan IP host yang menjalankan broker
#define MQTT_PORT    1883
```

**Penting**: `MQTT_BROKER` harus berupa IP address mesin yang menjalankan Mosquitto — bukan `localhost`, karena simulator berjalan di container terpisah.

---

## Pin Mapping

| Pin | Fungsi | Tipe |
|-----|--------|------|
| 5 | DHT22 #1 (suhu & kelembaban) | Digital |
| 4 | DHT22 #2 (suhu & kelembaban) | Digital |
| 26 | PIR #1 (deteksi gerak) | Digital Input |
| 25 | PIR #2 (deteksi gerak) | Digital Input |
| 32 | Gas Sensor #1 (CO₂ / kualitas udara) | Analog ADC |
| 33 | Gas Sensor #2 (CO₂ / kualitas udara) | Analog ADC |
| 35 | Potentiometer (simulasi arus/daya) | Analog ADC |
| 17 | Relay Master (emergency cutoff) | Digital Output |
| 21 | Relay Lampu | Digital Output |
| 23 | Relay AC | Digital Output |

---

## Arsitektur Firmware (FreeRTOS)

Firmware berjalan dengan dua task yang diproteksi oleh `xSemaphoreCreateMutex`:

### `taskReadSensors` (Priority 1)
Berjalan setiap 10 detik. Melakukan:
1. Baca DHT22 #1 dan #2 → rata-rata sebagai nilai suhu/kelembaban (sensor fusion)
2. Baca gas sensor ADC → konversi ke estimasi CO₂ ppm (400–2000 range)
3. Hitung lux sintetis: `350 + sin(ms/30000) * 120 + random(-15,15)`
4. Hitung comfort score (gabungan suhu, kelembaban, CO₂, lux)
5. Baca potentiometer → estimasi arus (0–15A) → hitung daya (W)
6. Baca PIR #1 dan #2 → estimasi jumlah orang + state (EMPTY/TRANSITIONING/OCCUPIED)
7. Jika mode **AUTO**: evaluasi apakah lampu/AC perlu dinyalakan berdasarkan kondisi sensor
8. Update `readings` struct (dilindungi mutex)

### `taskMQTT` (Priority 2)
Berjalan terus-menerus:
1. Pastikan koneksi WiFi dan MQTT aktif (reconnect otomatis jika terputus)
2. Setiap `PUBLISH_INTERVAL_MS` (10000ms): publish payload telemetry ke topik `tekra/wokwi/A1.01/telemetry`
3. Proses incoming commands via `mqtt.loop()`

---

## Logika AUTO vs OVERRIDE

ESP32 memiliki dua mode yang bisa dikontrol backend:

### Mode AUTO (default)
ESP32 memutuskan sendiri kapan menyalakan lampu/AC berdasarkan pembacaan sensor:

```
Lampu ON  → lux < 300
AC    ON  → state == OCCUPIED/TRANSITIONING
         OR suhu >= 28°C
         OR CO₂ >= 900 ppm
```

Keputusan AUTO hanya berlaku jika `master_relay == false`.

### Mode OVERRIDE
Backend mengambil alih kontrol penuh. ESP32 mengikuti instruksi `actuators` dari command yang diterima:
```json
{
  "mode": "OVERRIDE",
  "actuators": { "master_relay": false, "lights": true, "ac": true },
  "ac_setpoint": 26.0
}
```

### Master Relay
Jika `master_relay == true`, **semua relay dimatikan** tanpa memandang mode. Berfungsi sebagai emergency cutoff.

---

## Sensor Fusion

**Suhu & Kelembaban**: Jika kedua DHT22 terbaca valid → rata-rata digunakan. Jika satu gagal → gunakan yang tersedia. Jika keduanya gagal → gunakan nilai fallback (25°C, 60%).

**PIR & Estimasi Hunian**:
- Kedua PIR aktif → `OCCUPIED`, estimasi 15–35 orang
- Satu PIR aktif → `TRANSITIONING`, estimasi 1–10 orang
- Tidak ada PIR aktif → `EMPTY`, 0 orang

---

## Format Payload Telemetry

```json
{
  "device_id": "ESP-SIM-1",
  "room_id": "A1.01",
  "timestamp": "2026-05-24T08:30:00Z",
  "environment": {
    "temperature": 26.8,
    "humidity": 64.0,
    "heat_index": 28.1,
    "air_quality": 620,
    "lux": 412.0,
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

---

## Catatan Penting

- **Wokwi tidak mensimulasikan BH1750** — lux dibuat secara sintetis dengan fungsi sin(). Tidak ada feedback loop cahaya-lux di simulasi.
- **DHT22 di Wokwi** menggunakan library Adafruit DHT (bukan DHTesp). Library DHTesp mengembalikan 99°C secara konsisten di Wokwi — tidak kompatibel.
- **NTP sync**: Firmware mencoba sinkronisasi NTP (UTC+7). Jika gagal dalam 10 detik, timestamp fallback ke `"2026-01-01T00:00:00Z"`.
- **Anomaly detection dinonaktifkan** di backend untuk sumber `wokwi` — data simulasi tidak memicu notifikasi anomali.

---

## File Proyek

```
ESP_1_test/
├── src/main.cpp        Firmware utama (FreeRTOS + MQTT + sensor)
├── diagram.json        Skema rangkaian elektronik Wokwi
├── platformio.ini      Konfigurasi build (board, library deps)
└── wokwi.toml          Mapping firmware ke simulator Wokwi
```
