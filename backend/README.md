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
│     ├─ polsek.py                 # SUDAH JALAN: /polsek (GeoJSON), /polsek/{id}
│     ├─ kasus.py                  # SUDAH JALAN: GET, POST, PUT, DELETE
│     ├─ statistik.py              # SUDAH JALAN: /statistik, /statistik/tren
│     ├─ auth.py                   # SUDAH JALAN: /auth/login, /auth/me
│     └─ laporan.py                # /import/csv sudah jalan; TODO: /export (33)
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

## Impor CSV & CRUD kasus
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
