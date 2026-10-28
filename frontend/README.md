# Front End — Peta Rawan Kriminalitas

React (Vite) + Bootstrap + Leaflet. PIC: Dhea.

## Menjalankan

Butuh **Node.js 18+** (cek: `node -v`).

```
# 1. Nyalakan API tiruan (terminal 1) — dari root repo
cd mock-server
node server.js            # jalan di http://localhost:3000/api

# 2. Nyalakan front end (terminal 2)
cd frontend
npm install               # sekali saja, atau saat package.json berubah
npm run dev               # buka http://localhost:5173
```

Kalau di halaman peta muncul kotak hijau "Terhubung ke API: 27 wilayah Polsek dimuat", berarti beres.
Kotak merah = mock server belum jalan.

Saat backend asli siap (Minggu 4), tidak ada kode yang diubah: alamatnya sama
(`http://localhost:3000/api`). Kalau perlu alamat lain, salin `.env.example` jadi `.env`.

## Fitur yang butuh backend asli
Mock server hanya mendukung endpoint lama. Fitur di bawah ini memanggil API baru, jadi jalankan **backend asli**
(`uvicorn app.main:app --port 3000`, sudah termigrasi sampai `005_titik_kejadian.sql`):

- **Peta:** lapisan *Heatmap titik kejadian* (`GET /api/heatmap`, memakai `leaflet.heat`), saklar *Warna zona*,
  alat *Cek lokasi* (klik peta -> `GET /api/spasial/titik`), dan *Unduh rekap* CSV/XLSX (`GET /api/export`).
- **Titik Kejadian** (`/admin/titik`, operator & admin): tambah/ubah/hapus titik (klik peta kecil untuk koordinat),
  impor CSV `lat, lng, jenis, tanggal` dengan tombol "Periksa dulu" (dry run).
- **Master Data** (`/admin/master`, admin): tambah/ubah/hapus Polsek dan jenis kejahatan, unggah poligon GeoJSON.
- **Riwayat Perubahan** (`/admin/audit`, admin): siapa mengubah apa dan kapan.
- **Kelola Admin** (`/admin/pengguna`, admin): akun dibuat oleh admin (tidak ada pendaftaran mandiri).
- **Login:** setelah terlalu banyak percobaan gagal server membalas 429; pesannya (dengan lama tunggu) tampil di form.

Setelah `git pull`, jalankan `npm install` (ada dependensi baru: `leaflet.heat`).

## Struktur

```
src/
  main.jsx            # titik masuk (Bootstrap + router)
  App.jsx             # daftar rute
  api.js              # SEMUA panggilan API lewat sini (kontrak: docs/api-contract.md)
  auth.jsx            # sesi login (token di sessionStorage)
  styles.css          # warna zona + gaya tambahan
  components/         # Layout, Navbar, Ikon, ...
  pages/
    PetaPage.jsx        # beranda: filter + peta + heatmap + cek lokasi + unduh rekap
    DashboardPage.jsx   # kartu ringkasan + grafik Chart.js
    LoginPage.jsx       # login
    AdminPage.jsx       # kelola kasus & impor CSV rekap
    TitikPage.jsx       # titik kejadian (CRUD + impor CSV)         [baru]
    MasterDataPage.jsx  # Polsek, poligon, jenis kejahatan (admin)  [baru]
    AuditPage.jsx       # riwayat perubahan (admin)                 [baru]
    PenggunaPage.jsx    # kelola akun admin/operator
```

## Alur kerja Git (ringkas)

1. Mulai kerja: ambil update terbaru (`git pull origin main`, atau tombol **Fetch/Pull** di GitHub Desktop).
2. Buat branch fitur, misalnya `feat/kerangka-frontend`. **Jangan kerja langsung di `main`.**
3. Commit kecil dan sering, dengan pesan jelas: `feat: tambah halaman peta`.
4. Push, buat Pull Request, minta Monica review, lalu merge.
5. Jangan commit: `node_modules/`, `dist/`, `.env` (sudah ada di `.gitignore`).
