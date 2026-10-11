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

## Struktur
```
backend/
├─ app/
│  ├─ main.py          # titik masuk: CORS, handler error, daftar router (prefix /api)
│  ├─ config.py        # baca .env di root repo (DB_*, CORS_ORIGINS, JWT_*)
│  ├─ db.py            # connection pool + dependency `Conn`
│  ├─ errors.py        # ApiError + format error seragam {"error": {kode, pesan, detail}}
│  ├─ params.py        # helper parse query (mis. "1,16" -> [1, 16]), validasi zona
│  └─ routers/         # satu file per kelompok endpoint
│     ├─ health.py  referensi.py   # SUDAH JALAN: /health, /jenis, /tahun
│     ├─ polsek.py                 # TODO: /polsek, /polsek/{id}          (tugas 17)
│     ├─ kasus.py                  # TODO: GET (18), POST/PUT/DELETE      (26)
│     ├─ statistik.py              # TODO: /statistik, /statistik/tren    (19)
│     ├─ auth.py                   # TODO: /auth/login, /auth/me          (25)
│     └─ laporan.py                # TODO: /import/csv (26), /export (33)
├─ db/
│  ├─ migrations/      # skema + fungsi zonasi + seed jenis (run.sh)
│  └─ seed/            # impor CSV bersih + verifikasi (import.sh)
└─ tests/
```
Endpoint yang belum dikerjakan membalas `501 BELUM_DIIMPLEMENTASI` (format error sesuai kontrak), tapi **parameter query sudah divalidasi** — tinggal isi logikanya.

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

Tips: polygon untuk GeoJSON → `ST_AsGeoJSON(geom)::json` di SQL. Setelah ubah data kasus → `SELECT refresh_zona_kerawanan();`.

## Masalah umum
| Gejala | Solusi |
|---|---|
| `/api/health` → 503 `DATABASE_TIDAK_TERSEDIA` | `docker compose ps` — DB harus Up. Cek `DB_PORT` & `DB_PASSWORD` di `.env` (root repo, bukan di `backend/`) |
| `password authentication failed` | Password di `.env` beda dengan yang dipakai saat DB pertama dibuat → `docker compose down -v`, `up -d`, migrasi + impor ulang |
| `ModuleNotFoundError: app` | Jalankan `uvicorn` dan `pytest` dari folder `backend/` |
| `Address already in use` (port 3000) | Mock server masih jalan, atau pakai `--port 3001` |
| Front end kena CORS | Isi `CORS_ORIGINS` di `.env` dengan alamat front end (mis. `http://127.0.0.1:5500`) lalu restart |
