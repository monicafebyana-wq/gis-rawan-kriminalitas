# Backend — FastAPI

Implementasi [`docs/api-contract.md`](../docs/api-contract.md). Python **3.10+**, FastAPI, psycopg 3 (SQL langsung, tanpa ORM, agar fungsi PostGIS mudah dipakai).

## Menjalankan
Prasyarat: database sudah menyala, termigrasi, dan terisi (lihat README root: *Setup Database → Migrasi → Impor Data*), serta file `.env` di **root repo**.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 3000
```
Kalau PowerShell menolak mengaktifkan venv: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, lalu coba lagi.

| URL | Fungsi |
|---|---|
| http://localhost:3000/api/health | Cek API + koneksi DB + versi PostGIS |
| http://localhost:3000/docs | Dokumentasi interaktif (Swagger), bisa langsung coba endpoint |
| http://localhost:3000/api/jenis | Contoh endpoint yang sudah jalan |

Tes: `pytest` (dari folder `backend/`). Tes yang butuh DB otomatis dilewati kalau DB belum menyala.
Tes yang menulis data memakai **tahun fiktif 2098/2099** dan akun sementara `uji_*`, lalu membersihkannya sendiri — data asli (2024) tidak tersentuh.
Setelah menarik pembaruan: `pip install -r requirements-dev.txt` (ada paket baru: pyjwt, bcrypt).

## Struktur
```
backend/
├─ app/
│  ├─ main.py          # titik masuk: CORS, handler error, daftar router (prefix /api)
│  ├─ config.py        # baca .env di root repo (DB_*, CORS_ORIGINS, JWT_*)
│  ├─ db.py            # connection pool + dependency `Conn`
│  ├─ errors.py        # ApiError + format error seragam {"error": {kode, pesan, detail}}
│  ├─ security.py      # hash password (bcrypt) + token JWT
│  ├─ deps.py          # dependency login & peran: Pengguna (operator/admin), Admin (khusus admin)
│  ├─ buat_pengguna.py # CLI membuat akun admin/operator
│  ├─ params.py        # helper parse query (mis. "1,16" -> [1, 16]), validasi zona
│  ├─ services/
│  │  ├─ zonasi.py     # kategori_zona(), refresh_zona(), ambil_zona() — pembungkus fungsi SQL zonasi
│  │  ├─ rekap.py      # query rekap per Polsek (dipakai /polsek & /statistik), tentukan_tahun()
│  │  └─ impor_csv.py  # baca + validasi CSV rekap (nomor baris di setiap error), simpan ke DB
│  └─ routers/         # satu file per kelompok endpoint
│     ├─ health.py  referensi.py   # SUDAH JALAN: /health, /jenis, /tahun
│     ├─ polsek.py                 # SUDAH JALAN: /polsek (GeoJSON), /polsek/{id}; admin: tambah/ubah/hapus Polsek, unggah poligon
│     ├─ kasus.py                  # SUDAH JALAN: GET, POST, PUT, DELETE
│     ├─ statistik.py              # SUDAH JALAN: /statistik, /statistik/tren
│     ├─ auth.py                   # SUDAH JALAN: /auth/login, /auth/me, /auth/ubah-password
│     ├─ pengguna.py               # SUDAH JALAN: /pengguna (daftar/tambah/ubah/hapus akun, khusus admin)
│     ├─ audit.py                  # SUDAH JALAN: GET /audit (riwayat perubahan, khusus admin)
│     ├─ titik.py                  # SUDAH JALAN: /heatmap (publik), /titik (CRUD + impor CSV)
│     ├─ spasial.py                # SUDAH JALAN: /spasial/titik, /terdekat, /bbox (PostGIS)
│     └─ laporan.py                # SUDAH JALAN: /import/csv, /export (csv/xlsx)
├─ db/
│  ├─ migrations/      # skema + fungsi zonasi + seed jenis (run.sh)
│  └─ seed/            # impor CSV bersih + verifikasi (import.sh)
└─ tests/
```
Endpoint yang belum dikerjakan membalas `501 BELUM_DIIMPLEMENTASI` (format error sesuai kontrak), tapi **parameter query sudah divalidasi** — tinggal isi logikanya.

## Login, akun, dan hak akses

Endpoint `GET` bersifat publik. Yang mengubah data butuh login:

| Aksi | operator | admin |
|---|:-:|:-:|
| `POST /api/kasus`, `PUT /api/kasus/{id}`, `POST /api/import/csv` | ✅ | ✅ |
| `DELETE /api/kasus/{id}` | ❌ 403 | ✅ |
| `POST/PUT/DELETE /api/polsek`, `/api/jenis`, `POST /api/polsek/geojson`, `PUT /api/polsek/{id}/poligon`, `GET /api/audit` | ❌ 403 | ✅ |
| `GET/POST /api/pengguna`, `PUT/DELETE /api/pengguna/{id}` (kelola akun) | ❌ 403 | ✅ |
| `POST /api/auth/ubah-password` (ganti password sendiri) | ✅ | ✅ |

**1. Buat akun pertama** (database harus menyala, venv aktif, dari folder `backend/`; password ditanya dan tidak tampil):
```powershell
python -m app.buat_pengguna admin --peran admin
python -m app.buat_pengguna petugas1 --peran operator
```
Password minimal 8 karakter, maksimal 72 byte. Jalankan lagi dengan username yang sama untuk mengganti password/peran. Password disimpan sebagai hash bcrypt, tidak pernah plaintext.

**2. Login lewat Swagger** (`/docs`): jalankan `POST /api/auth/login` (Try it out) → salin nilai `token` → klik tombol **Authorize** di kanan atas → tempel token → semua endpoint terkunci ikut terbuka.
Dari front end/curl: kirim header `Authorization: Bearer <token>`. Token berlaku 24 jam (`JWT_BERLAKU_DETIK`).

**3. Wajib sebelum dipakai sungguhan:** isi `JWT_SECRET` di `.env` dengan string acak panjang (minimal 32 karakter):
```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Mengganti secret membuat semua token lama tidak berlaku.

Kode status: tidak login / token salah → `401`; peran kurang → `403`. Peran dibaca dari database di tiap request, jadi akun yang dihapus langsung kehilangan akses.

## Mendaftarkan admin/operator baru
Alur: **admin yang sudah login mendaftarkan akun baru** (tidak ada pendaftaran mandiri). Admin pertama dibuat lewat CLI di atas.
```
POST /api/pengguna        {"username": "petugas2", "password": "min-8-karakter", "peran": "admin"}   # peran default: operator
PUT  /api/pengguna/{id}   {"peran": "operator", "password": "reset-baru-123"}                       # keduanya opsional, minimal satu
DELETE /api/pengguna/{id}
```
Pengaman: tidak bisa menghapus akun sendiri, dan sistem menolak aksi yang membuat admin habis (`409 AKSI_DITOLAK`).

## Fitur tambahan
**Migrasi baru:** jalankan `docker exec gis_kriminalitas_db sh /migrations/run.sh` (menerapkan `004_audit_log.sql`) dan `pip install -r requirements-dev.txt` (paket baru: openpyxl).

- **Ekspor:** `GET /api/export?format=csv|xlsx&tahun=&jenis=&polsek=` (publik). Kolom CSV sama dengan format impor (+ `Total`, `Zona` yang diabaikan saat impor ulang); XLSX berwarna per zona + baris TOTAL. Header `Content-Disposition` sudah di-expose untuk CORS.
- **Master data (admin):** `POST/PUT/DELETE /api/polsek` dan `/api/jenis`. Polsek yang masih punya kasus dan 18 jenis baku (dipakai impor CSV) tidak bisa dihapus -> `409`. Jenis baru diisi per kasus, bukan lewat impor CSV.
- **Poligon (admin):** `POST /api/polsek/geojson` (form-data `file`, `dry_run`) atau `PUT /api/polsek/{id}/poligon`. Validasi sama dengan `import_poligon.sql` (geometri diperbaiki otomatis, kotak wilayah, luas, tumpang tindih); gagal = tidak ada yang tersimpan. **Pakai `dry_run=true` dulu.**
- **Audit log:** `GET /api/audit?entitas=&aksi=&username=&dari=&sampai=&page=&limit=` (admin). Mencatat tambah/ubah/hapus kasus, akun, Polsek, jenis, poligon, impor CSV, ganti password. Password tidak pernah dicatat.
- **Spasial (publik):** `GET /api/spasial/titik?lat=&lng=` (titik masuk wilayah mana; di luar wilayah -> Polsek terdekat + jarak), `/spasial/terdekat?lat=&lng=&limit=&radius_m=`, `/spasial/bbox?min_lng=&min_lat=&max_lng=&max_lat=&geometri=` (GeoJSON).
- **Titik kejadian & heatmap:** tabel `titik_kejadian` (lat/lng per kejadian), **terpisah** dari rekap kasus -> tidak mengubah jumlah kasus/zona. Butuh migrasi `005_titik_kejadian.sql`.
  - `GET /api/heatmap?tahun=&dari=&sampai=&jenis=&polsek=&grid=0.002` (publik) -> `{"grid_derajat", "total_titik", "maks_bobot", "data": [{"lat", "lng", "bobot"}]}`. Titik dirangkum per sel grid (0.001 derajat ~ 110 m, minimum 0.0005), jadi koordinat persis tidak dibuka ke publik. `bobot / maks_bobot` = intensitas untuk Leaflet.heat. Tanpa `tahun` = semua tahun.
  - `GET /api/titik` (login) daftar titik persis; `POST /api/titik` `{"lat", "lng", "id_jenis", "tanggal"}` (operator/admin); `PUT /api/titik/{id}` (semua field boleh diubah); `DELETE` (admin). `id_polsek` otomatis dari poligon (null bila di luar wilayah).
  - `POST /api/titik/import` (form-data `file`, `dry_run`): CSV dengan kolom `lat, lng, jenis, tanggal`. `jenis` boleh kode (`CURAT`), nama, atau id; tanggal `YYYY-MM-DD` atau `DD/MM/YYYY`; pemisah `,` atau `;` (dengan `;` koma dibaca desimal). Semua baris valid atau tidak ada yang tersimpan. Maks 5 MB / 20.000 baris.
  - Koordinat divalidasi masuk kotak wilayah (lng 107.2-108.2, lat -7.6 s/d -6.6) untuk menangkap lat/lng tertukar.
- **Batas login:** 5 gagal per (IP + username) atau 30 gagal per IP dalam 15 menit -> `429 TERLALU_BANYAK_PERCOBAAN` + header `Retry-After`. Diatur lewat `LOGIN_MAKS_GAGAL`, `LOGIN_MAKS_GAGAL_IP`, `LOGIN_JENDELA_DETIK` di `.env`. Hitungan disimpan di memori (cukup untuk 1 worker). Di belakang reverse proxy, jalankan uvicorn dengan `--proxy-headers` agar IP yang terbaca IP klien asli.

## Impor CSV & CRUD kasus
- `PUT /api/kasus/{id}` boleh mengubah **semua field** (`id_polsek`, `id_jenis`, `tahun`, `jumlah`); kirim hanya yang berubah. Kombinasi polsek+jenis+tahun yang bentrok -> `409`; zona tahun lama & baru dihitung ulang.
- `POST /api/import/csv` (form-data): `file` (.csv, maks 2 MB), `tahun`, `mode` (`timpa` default = hapus data tahun itu dulu; `tambah` = gabung/perbarui), `dry_run` (`true` = hanya validasi).
- Format CSV sama dengan `data/rekap_kriminalitas_2024.csv`: kolom `Polsek` + 18 kolom jenis (kolom `Jumlah` opsional, dicek = jumlah 18 jenis). Pemisah `,` atau `;` dan file dari Excel (BOM) didukung. Nama Polsek dinormalisasi (`POLSEK BALE ENDAH` = `Bale Endah`).
- **Gunakan `dry_run=true` dulu.** Kalau ada yang salah, respons `400` memuat daftar `detail` dengan nomor baris dan alasannya, dan **tidak ada** yang tersimpan.
- Setiap tambah/ubah/hapus/impor otomatis memanggil `refresh_zona()`, jadi zona di peta langsung ikut berubah.

## Cara mengerjakan sebuah endpoint
1. Buka file router-nya, hapus `raise belum_diimplementasi(...)`, tulis logikanya.
2. Pakai `conn: Conn` untuk akses database:
   ```python
   from app.db import Conn

   @router.get("/contoh")
   def contoh(conn: Conn, tahun: int):
       rows = conn.execute("SELECT * FROM v_zona_polsek WHERE tahun = %s", (tahun,)).fetchall()   # list[dict]
       return {"data": rows}
   ```
3. **Selalu** kirim nilai lewat parameter `%s` — jangan menyusun SQL dengan f-string/`+` (rawan SQL injection).
4. Error: `raise validasi_gagal(...)`, `raise tidak_ditemukan(...)` dari `app/errors.py` — bukan `HTTPException`.
5. Sesuaikan bentuk respons dengan `docs/api-contract.md` dan `data/mock/*.json` (Dhea memakai bentuk itu). Kalau harus berbeda, **ubah kontraknya dulu** dan kabari.
6. Tambah tes di `tests/`, lalu buat PR.

Zonasi: ambang 60/30 hanya ditulis di SQL (`hitung_kategori_zona`). Dari Python pakai `app/services/zonasi.py` — setelah endpoint mengubah data kasus, panggil `zonasi.refresh_zona(conn, tahun)`.

Tips: polygon untuk GeoJSON → `ST_AsGeoJSON(geom)::json` di SQL. Setelah ubah data kasus → `SELECT refresh_zona_kerawanan();`.

## Masalah umum
| Gejala | Solusi |
|---|---|
| `/api/health` → 503 `DATABASE_TIDAK_TERSEDIA` | `docker compose ps` — DB harus Up. Cek `DB_PORT` & `DB_PASSWORD` di `.env` (root repo, bukan di `backend/`) |
| `password authentication failed` | Password di `.env` beda dengan yang dipakai saat DB pertama dibuat → `docker compose down -v`, `up -d`, migrasi + impor ulang |
| `ModuleNotFoundError: app` | Jalankan `uvicorn` dan `pytest` dari folder `backend/` |
| `Address already in use` (port 3000) | Mock server masih jalan, atau pakai `--port 3001` |
| Front end kena CORS | Isi `CORS_ORIGINS` di `.env` dengan alamat front end (mis. `http://127.0.0.1:5500`) lalu restart |
