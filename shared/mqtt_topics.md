# Struktur Topik MQTT

Semua topik diawali dengan `tekra/`. Setiap ruangan memiliki dua topik: satu untuk data sensor dan satu untuk perintah aktuator.

## Topik Produksi (Hardware Fisik)

| Topik | Arah | Keterangan |
|-------|------|------------|
| `tekra/room/{room_id}/telemetry` | ESP32 → Server | Data sensor dikirim setiap 10 detik |
| `tekra/room/{room_id}/commands` | Server → ESP32 | Perintah kontrol aktuator dari backend |

## Wildcard Subscriber

| Subscriber | Subscribe ke | Tujuan |
|------------|-------------|--------|
| Telegraf | `tekra/room/+/telemetry` | Simpan semua telemetry ke QuestDB |
| FastAPI Backend | `tekra/room/+/telemetry` | Proses anomali, auto-control, broadcast WS |

`+` adalah wildcard satu level MQTT — mencocokkan tepat satu segmen, contoh `A1.01`.

## Konvensi Room ID

Format: `{inisial_gedung}{lantai}.{nomor_ruang}`

| Room ID | Arti |
|---------|------|
| `A1.01` | Gedung A, Lantai 1, Ruang 01 |
| `A1.02` | Gedung A, Lantai 1, Ruang 02 |
| `A2.03` | Gedung A, Lantai 2, Ruang 03 |
| `B1.01` | Gedung B, Lantai 1, Ruang 01 |

## Quality of Service (QoS)

| Topik | QoS | Alasan |
|-------|-----|--------|
| Telemetry | 0 (At most once) | Data sensor baru akan menggantikan yang lama; kehilangan satu pesan tidak kritis |
| Commands | 1 (At least once) | Perintah aktuator harus tersampaikan; duplikat tidak berpengaruh (idempotent) |

## Topik Simulasi (Pengembangan & Demo)

Digunakan selama fase pengembangan saat hardware fisik belum tersedia.  
Backend membedakan sumber `room` vs `wokwi` dari nama topik untuk menonaktifkan anomaly detection pada data simulasi.

| Topik | Keterangan |
|-------|------------|
| `tekra/wokwi/{room_id}/telemetry` | Data dari simulasi ESP32 (Wokwi) |
| `tekra/wokwi/{room_id}/commands` | Command ke simulasi |
