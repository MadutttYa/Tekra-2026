# ESP_2_test — Simulasi ESP32 Wokwi (Ruangan A1.02)

Proyek PlatformIO + Wokwi yang mensimulasikan satu unit ESP32 untuk ruangan **A1.02 (Gedung-A, Lantai 1)**. Firmware dan skema rangkaian identik dengan `ESP_1_test` — hanya berbeda pada Room ID dan Device ID.

---

## Identitas Perangkat

| Parameter | Nilai |
|-----------|-------|
| Room ID | `A1.02` |
| Device ID | `ESP-SIM-2` |
| Building | `Gedung-A` |
| Floor | `1` |
| Topik telemetry | `tekra/wokwi/A1.02/telemetry` |
| Topik command | `tekra/wokwi/A1.02/commands` |

---

## Cara Menjalankan

### Prasyarat
- PlatformIO (`pip install platformio` atau ekstensi VS Code)
- Wokwi VS Code Extension
- Broker MQTT jalan di IP yang dikonfigurasi (`MQTT_BROKER` di `main.cpp`)

### Build & Simulasi
```bash
cd Simulation/ESP_2_test
pio run                      # compile firmware → .pio/build/esp32dev/firmware.bin
```

Buka folder di VS Code, lalu jalankan **Wokwi: Start Simulator**.

---

## Konfigurasi Jaringan

```cpp
#define WIFI_SSID    "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define MQTT_BROKER  "10.200.64.195"   // Ganti dengan IP host lokal
#define MQTT_PORT    1883
```

---

## Perbedaan dengan ESP_1_test

Hanya dua konstanta yang berbeda:

```cpp
// ESP_1_test:
#define ROOM_ID   "A1.01"
#define DEVICE_ID "ESP-SIM-1"

// ESP_2_test:
#define ROOM_ID   "A1.02"
#define DEVICE_ID "ESP-SIM-2"
```

Seluruh logika firmware (FreeRTOS tasks, sensor fusion, AUTO/OVERRIDE, format payload) identik. Lihat [ESP_1_test/README.md](../ESP_1_test/README.md) untuk dokumentasi lengkap.

---

## Menjalankan Kedua Simulasi Bersamaan

Kedua simulator bisa berjalan paralel di VS Code menggunakan dua jendela/instance terpisah:

1. Buka `Simulation/ESP_1_test` di VS Code → Start Simulator
2. Buka `Simulation/ESP_2_test` di VS Code (new window) → Start Simulator

Keduanya terhubung ke broker MQTT yang sama. Backend akan menerima telemetry dari dua ruangan secara bersamaan dan menampilkan keduanya di dashboard.

---

## File Proyek

```
ESP_2_test/
├── src/main.cpp        Firmware utama (identik dengan ESP_1_test, beda ROOM_ID)
├── diagram.json        Skema rangkaian elektronik Wokwi
├── platformio.ini      Konfigurasi build
└── wokwi.toml          Mapping firmware ke simulator Wokwi
```
