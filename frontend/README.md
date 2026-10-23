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

## Struktur

```
src/
  main.jsx            # titik masuk (Bootstrap + router)
  App.jsx             # daftar rute
  api.js              # SEMUA panggilan API lewat sini (kontrak: docs/api-contract.md)
  styles.css          # warna zona + gaya tambahan
  components/Navbar.jsx
  pages/
    PetaPage.jsx      # beranda: filter + peta Leaflet + legenda + popup (task 15, 20, 21, 23)
    DashboardPage.jsx # kartu ringkasan + grafik Chart.js    (task 29, 30, 31)
    LoginPage.jsx     # login admin                    (task 32)
    AdminPage.jsx     # CRUD & impor CSV               (task 32)
```

## Alur kerja Git (ringkas)

1. Mulai kerja: ambil update terbaru (`git pull origin main`, atau tombol **Fetch/Pull** di GitHub Desktop).
2. Buat branch fitur, misalnya `feat/kerangka-frontend`. **Jangan kerja langsung di `main`.**
3. Commit kecil dan sering, dengan pesan jelas: `feat: tambah halaman peta`.
4. Push, buat Pull Request, minta Monica review, lalu merge.
5. Jangan commit: `node_modules/`, `dist/`, `.env` (sudah ada di `.gitignore`).
