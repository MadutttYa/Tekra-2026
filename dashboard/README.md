# Dashboard — Intelligent Smart Classroom System

Dashboard monitoring dan kontrol ruang kelas. Diimplementasikan sebagai **single-file** (`index.html`) tanpa framework atau build step — cukup buka di browser.

---

## Cara Membuka

```bash
# Buka langsung di browser:
firefox dashboard/index.html
# atau
xdg-open dashboard/index.html
```

Pastikan backend sudah berjalan di `http://localhost:8000`. Dashboard akan terhubung otomatis via WebSocket saat halaman dimuat.

---

## Seksi Dashboard

### 1. Dasbor Utama (Home)
Halaman pertama yang terlihat saat membuka dashboard.

**Kartu Statistik Agregat** (kiri atas):
- Rata-rata konsumsi daya seluruh ruangan (W)
- Rata-rata skor kenyamanan (0–100)
- Jumlah ruangan aktif / total ruangan
- Jumlah notifikasi belum dibaca

**Kalender Interaktif** (tengah):
- Navigasi bulan dengan tombol `‹` / `›`
- Titik berwarna di setiap tanggal menandai:
  - 🔵 Biru — ada jadwal kuliah
  - 🟢 Hijau — ada peminjaman disetujui
  - 🔴 Merah — hari libur
- Klik tanggal → panel samping menampilkan daftar event hari itu

**Panel Notifikasi** (kanan): Log anomali real-time dengan tombol acknowledge.

**Form Peminjaman Cepat** (bawah kalender): Ajukan peminjaman langsung dari halaman utama.

---

### 2. Tampilan Detail
Monitoring dan kontrol per-ruangan.

**Grid Kartu Ruangan**: Semua ruangan ditampilkan sebagai kartu kecil berisi:
- Nama ruangan & gedung
- Suhu, skor kenyamanan, daya saat ini
- Status hunian (badge: OCCUPIED / EMPTY / TRANSITIONING)
- Indikator mode (AUTO / OVERRIDE / HOLIDAY)

**Klik kartu** → Panel Detail Ruangan terbuka, berisi:

*6 Kartu Metrik:*
| Metrik | Keterangan |
|--------|------------|
| Suhu | °C + kelembaban & heat index |
| Kenyamanan | Skor 0–100 |
| Kualitas Udara | CO₂ ppm + level |
| Daya | Watt real-time |
| Hunian | Estimasi jumlah orang |
| Cahaya | Lux |

*3 Grafik Historis (1 jam terakhir):*
- Suhu & Kelembaban
- Kualitas Udara & Lux
- Konsumsi Daya

*Panel Kontrol (hanya mode OVERRIDE):*
- Ganti mode ruangan (AUTO / OVERRIDE / HOLIDAY)
- Toggle lampu ON/OFF
- Toggle AC ON/OFF + setpoint suhu
- Master relay (emergency cutoff)

Data di panel detail diperbarui otomatis setiap kali WebSocket menerima `sensor_update` untuk ruangan yang sedang dibuka.

---

### 3. Jadwal Kuliah
Manajemen jadwal kuliah per ruangan.

- Pilih ruangan dari dropdown → tampil grid mingguan (Sen–Min)
- Setiap slot menampilkan mata kuliah, dosen, waktu mulai–selesai
- Form tambah jadwal: pilih ruangan, hari, jam mulai, jam selesai, nama mata kuliah, dosen
- Jadwal yang aktif berdampak pada auto-control sistem

---

### 4. Peminjaman Ruangan
Sistem booking ruangan.

- **Form Ajukan Peminjaman**: pilih ruangan, tanggal, jam, nama peminjam, keperluan
- **Daftar Pending**: peminjaman menunggu persetujuan, tombol Setujui / Tolak
- **Peminjaman Disetujui**: riwayat booking yang sudah approved per ruangan
- Peminjaman yang disetujui berlaku setara jadwal kuliah dalam auto-control

---

### 5. Hari Libur
Manajemen hari libur kampus/nasional.

- Form tambah: pilih tanggal, masukkan nama hari libur
- Daftar semua hari libur terdaftar dengan tombol hapus
- Pada hari libur, seluruh auto-control dinonaktifkan dan kehadiran yang terdeteksi memicu alert CRITICAL

---

## Arsitektur Teknis

### Koneksi Backend

Dashboard berkomunikasi dengan backend melalui dua jalur:

**REST API** (saat load awal):
```javascript
const BASE = "http://localhost:8000";
// Contoh:
fetch(`${BASE}/rooms`)               // daftar ruangan
fetch(`${BASE}/rooms/${id}/latest`)  // data sensor terbaru
fetch(`${BASE}/holidays`)            // daftar hari libur
```

**WebSocket** (real-time updates):
```javascript
ws = new WebSocket("ws://localhost:8000/ws");
ws.onmessage = (e) => {
  const { event, data } = JSON.parse(e.data);
  if (event === "sensor_update") { /* perbarui UI */ }
  if (event === "new_notification") { /* tambah ke panel notifikasi */ }
};
```

### Safe Fetch Helper

Semua request REST menggunakan fungsi `sf()` yang mengembalikan fallback jika request gagal (non-OK status, network error, JSON parse error). Ini mencegah crash dashboard akibat endpoint yang belum tersedia atau backend yang sedang restart:

```javascript
async function sf(url, fallback = null) {
  try {
    const r = await fetch(url);
    if (!r.ok) return fallback;
    return await r.json();
  } catch { return fallback; }
}
```

### Urutan Inisialisasi

```javascript
async function init() {
  connectWS();          // 1. WebSocket PERTAMA — agar tidak ada data yang terlewat
  await loadRooms();    // 2. Daftar ruangan
  await loadLatest();   // 3. Data sensor awal
  await loadAll();      // 4. Jadwal, booking, holiday untuk kalender
  renderCalendar();     // 5. Render kalender
  renderRoomCards();    // 6. Render grid ruangan
}
```

WebSocket selalu dikoneksikan pertama untuk memastikan update real-time tidak terlewat selama proses loading.

### Normalisasi Data

Data dari REST `/latest` dan WebSocket `sensor_update` memiliki format berbeda. Fungsi `normLatest(d)` mengkonversi respons flat dari `/latest` ke format nested yang sama dengan WebSocket:

```javascript
// Field mapping dari /latest:
// d.power_w      → power.power_w
// d.state        → occupancy.state
// d.energy       → power.energy
// dst.
```

### State Management

Semua data disimpan dalam variabel global:
- `rooms[]` — daftar ruangan
- `roomLatest{}` — data sensor terbaru per room_id (key: room_id)
- `allSchedules{}` — semua jadwal per room_id
- `allBookings{}` — semua booking per room_id
- `allHolidays[]` — semua hari libur
- `currentDetailRoom` — room_id panel detail yang sedang terbuka

---

## Desain Visual

Mengikuti DESIGN.md dengan tema **glassmorphism**:
- Background: gradient gelap `#0f1117` → `#1a1f2e`
- Kartu: `rgba(24, 28, 37, 0.70)` + `backdrop-filter: blur(12px)`
- Aksen: `#4f8ef7` (biru), `#7b5ea7` (ungu)
- Tipografi: Inter (Google Fonts)
- Color tokens dari Material Design 3

---

## Catatan

- Dashboard tidak membutuhkan web server — bisa dibuka langsung sebagai file lokal (`file://`)
- Jika backend restart, WebSocket otomatis mencoba reconnect setiap 3 detik
- Grafik historis menggunakan Canvas API native (tanpa library charting eksternal)
- Semua operasi kalender bersifat client-side murni (tidak ada request tambahan saat navigasi bulan)
