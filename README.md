# Sistem Informasi Geografis Pemetaan Titik Rawan Kriminalitas Berbasis Zonasi

Tugas 1 mata kuliah **Teknologi Pemetaan Berbasis Web (TPBW)** — Telkom University.

**Tim:** Monica Febyana (101032330068) · Dhea Kusuma Wardhani (101032330059)

## Deskripsi
Aplikasi web pemetaan yang memvisualisasikan sebaran kasus kejahatan tahun 2024 per wilayah Polsek (27 Polsek, 18 jenis kejahatan, 1.163 kasus) dan mengelompokkan wilayah ke dalam zona kerawanan:

| Zona | Kriteria |
|------|----------|
| Rawan Tinggi | >= 60 kasus |
| Rawan Sedang | 30-59 kasus |
| Rawan Rendah | < 30 kasus |

## Fitur Utama
- Peta interaktif (Leaflet.js) dengan warna zona, legenda, dan popup detail per wilayah
- Filter berdasarkan Polsek/wilayah, jenis kejahatan, dan periode
- Heatmap intensitas kasus per wilayah
- Dashboard statistik (kartu ringkasan, grafik batang, tren)
- Login admin/operator, CRUD data, dan impor rekap CSV
- Ekspor ringkasan laporan

## Teknologi
- **Front end:** HTML5, CSS3, JavaScript, Bootstrap, Leaflet.js, Chart.js
- **Back end:** Python 3.10+ dengan FastAPI (psycopg 3, connection pool)
- **Database:** PostgreSQL + PostGIS
- **Data:** CSV (atribut kriminalitas), GeoJSON WGS 84 (batas wilayah)

## Struktur Repo
```
backend/      # FastAPI: REST API, autentikasi, impor CSV, zonasi (+ db/ migrasi & seed)
frontend/     # UI, peta Leaflet, dashboard
mock-server/  # server API tiruan (untuk frontend sebelum backend siap)
data/         # CSV sumber, GeoJSON wilayah
  bersih/     # CSV hasil normalisasi (siap impor ke DB)
  geojson/    # taruh polsek.geojson (poligon asli) di sini
  mock/       # data contoh JSON sesuai API contract
docs/         # API contract, wireframe, laporan
```

## Pembagian Peran
| Area | PIC |
|------|-----|
| Data, database, API, zonasi, autentikasi, deploy | Monica |
| Data spasial, UI, peta, filter, dashboard | Dhea |
| API contract, pengujian, dokumentasi, demo | Berdua |

## Setup Database (PostgreSQL + PostGIS)

> Yang butuh database lokal terutama **backend**. Front end bisa jalan dengan `data/mock/*.json` sampai integrasi (Minggu 4).

### Opsi A — Docker (disarankan, sama persis di semua laptop)
1. Install **Docker Desktop** (Windows butuh WSL2, ikuti petunjuk installer), lalu buka dan tunggu statusnya *Running*.
2. Di root repo, salin env: `cp .env.example .env` (Windows PowerShell: `copy .env.example .env`), lalu ganti `DB_PASSWORD`.
3. Jalankan database:
   ```
   docker compose up -d
   ```
4. Cek sudah hidup dan PostGIS aktif:
   ```
   docker compose ps
   docker exec -it gis_kriminalitas_db psql -U postgres -d gis_kriminalitas -c "SELECT PostGIS_Version();"
   ```
   Kalau muncul versi PostGIS (mis. `3.4 ...`), berarti berhasil.
5. Perintah sehari-hari:
   | Perintah | Fungsi |
   |---|---|
   | `docker compose up -d` | nyalakan DB |
   | `docker compose stop` | matikan DB (data aman) |
   | `docker compose logs -f db` | lihat log |
   | `docker exec -it gis_kriminalitas_db psql -U postgres -d gis_kriminalitas` | masuk ke psql |
   | `docker compose down -v` | **hapus DB beserta datanya** (reset dari nol) |

Koneksi untuk backend: `postgresql://DB_USER:DB_PASSWORD@localhost:DB_PORT/DB_NAME` (nilai dari `.env`).
Bisa juga dilihat lewat pgAdmin/DBeaver dengan host `localhost`, port sesuai `DB_PORT`.

### Opsi B — Instal langsung di laptop (tanpa Docker)
- **Windows:** unduh PostgreSQL dari postgresql.org (installer EDB), centang **Stack Builder** di akhir → pilih *Spatial Extensions* → **PostGIS**. Lalu di pgAdmin/psql:
  ```sql
  CREATE DATABASE gis_kriminalitas;
  \c gis_kriminalitas
  CREATE EXTENSION postgis;
  SELECT PostGIS_Version();
  ```
- **macOS:** `brew install postgresql@16 postgis`, lalu `brew services start postgresql@16` dan perintah SQL di atas.
- **Ubuntu/Debian:** `sudo apt install postgresql postgis`, lalu perintah SQL di atas (`sudo -u postgres psql`).

### Masalah umum
| Gejala | Solusi |
|---|---|
| `port is already allocated` / port 5432 bentrok | Ubah `DB_PORT=5433` di `.env`, lalu `docker compose up -d` lagi |
| `Cannot connect to the Docker daemon` | Docker Desktop belum jalan — buka dulu aplikasinya |
| `password authentication failed` setelah ganti password di `.env` | Password hanya dipakai saat DB pertama dibuat. Reset: `docker compose down -v` lalu `docker compose up -d` (data hilang, impor ulang) |
| `extension "postgis" is not available` (Opsi B) | PostGIS belum terpasang — ulangi Stack Builder / `apt install postgis` |

### Berbagi skema & data antar anggota tim
Database **lokal masing-masing** (tidak dibagi lewat internet). Yang masuk Git: skema (`backend/db/migrations/*.sql`, dibuat Minggu 2) dan data bersih (`data/bersih/*.csv`). Siapa pun bisa membangun ulang DB yang sama dengan menjalankan migrasi + impor CSV.

## Migrasi Database (Skema)

Skema ada di `backend/db/migrations/` dan dijalankan berurutan oleh `run.sh` (yang sudah diterapkan otomatis dilewati):

| File | Isi |
|---|---|
| `001_buat_skema.sql` | 5 tabel: `polsek` (+ kolom `geom` PostGIS), `jenis_kejahatan`, `kasus_kejahatan`, `zona_kerawanan`, `pengguna` + indeks & constraint |
| `002_fungsi_zonasi.sql` | `hitung_kategori_zona()`, `refresh_zona_kerawanan(tahun)`, `sinkronkan_urutan_id()`, view `v_zona_polsek` |
| `003_seed_jenis_kejahatan.sql` | Data 18 jenis kejahatan |

Menjalankan (database harus sudah menyala):
```
docker compose up -d
docker exec gis_kriminalitas_db sh /migrations/run.sh
docker exec -it gis_kriminalitas_db psql -U postgres -d gis_kriminalitas -c "\dt"
```
> Pertama kali setelah menarik update ini, jalankan `docker compose up -d` lagi supaya folder `migrations` ikut terpasang di container.

Relasi: `kasus_kejahatan` mengacu ke `polsek` dan `jenis_kejahatan` (unik per polsek+jenis+tahun, jumlah >= 0); `zona_kerawanan` mengacu ke `polsek` (unik per polsek+tahun, nilai `tinggi`/`sedang`/`rendah`); `pengguna` berdiri sendiri (hanya simpan hash password).

Aturan penting:
- **Perubahan skema = file migrasi baru** (`003_...sql`, dst). Jangan edit file yang sudah dijalankan.
- Setelah impor/ubah data kasus, panggil `SELECT refresh_zona_kerawanan();` agar tabel zona ikut diperbarui.
- Kalau impor memakai id eksplisit dari CSV, akhiri dengan `SELECT sinkronkan_urutan_id();`.
- Reset total (hapus semua data): `docker compose down -v`, lalu `up -d` dan jalankan migrasi lagi.

## Impor Data ke Database

Memasukkan CSV bersih (`data/bersih/`) ke tabel `polsek` dan `kasus_kejahatan`, menghitung zona, lalu **memverifikasi** hasilnya.

```
docker compose up -d                                   # pasang mount baru (sekali setelah update repo)
docker exec gis_kriminalitas_db sh /migrations/run.sh  # terapkan migrasi (termasuk seed 18 jenis)
docker exec gis_kriminalitas_db sh /seed/import.sh     # impor + verifikasi
```
Hasil yang benar: tabel verifikasi berisi 6 baris berstatus `LULUS` dan di akhir muncul `Verifikasi LULUS, data tersimpan`:

| Pengecekan | Harus |
|---|---|
| Jumlah Polsek / jenis kejahatan | 27 / 18 |
| Baris `kasus_kejahatan` (27 x 18) | 486 |
| **Total kasus** | **1.163** |
| Total per Polsek vs kolom `Jumlah` di CSV | 0 selisih |
| Kategori zona vs CSV | 0 selisih |

- Kalau ada yang `GAGAL`, **semua perubahan dibatalkan otomatis** (rollback) dan skrip berhenti dengan error. Perbaiki CSV-nya, jalankan lagi.
- Aman dijalankan berulang: data tahun yang sama diganti, tidak digandakan. Kolom `geom` (poligon) tidak ikut terhapus.
- Kalau data memang berubah (mis. tahun baru dengan total berbeda): `sh /seed/import.sh <total_baru>`.
- Cek manual: `docker exec -it gis_kriminalitas_db psql -U postgres -d gis_kriminalitas -c "SELECT sum(jumlah) FROM kasus_kejahatan"` → `1163`.

## Impor Poligon Wilayah (PostGIS)

Memasukkan poligon dari `data/geojson/polsek_poligon.geojson` ke kolom `polsek.geom`, dengan **validasi geometri** otomatis. Jalankan setelah *Impor Data* (tabel `polsek` harus sudah terisi):

```
docker compose up -d                                       # pasang mount data/geojson (sekali setelah update repo)
docker exec gis_kriminalitas_db sh /seed/import_poligon.sh
```
Hasil yang benar: 12 pengecekan berstatus `LULUS`, lalu `Verifikasi LULUS, poligon tersimpan`, dan uji spasial di bawahnya menampilkan `Soreang`.

| Yang dicek | Menangkap masalah |
|---|---|
| 27 feature, `id_polsek` unik, semua ada di tabel `polsek` | feature hilang / id asing |
| Nama di GeoJSON = nama di database | id tertukar antar Polsek |
| Bukan kosong, tipe Polygon/MultiPolygon, **valid** (setelah `ST_MakeValid`), SRID 4326 | geometri rusak / self-intersection |
| Di dalam kotak Kab. Bandung (lon 107.2–108.2, lat -7.6 s/d -6.6) | lon/lat tertukar, koordinat UTM |
| Luas tiap wilayah 1–600 km² | poligon degenerate / salah satuan |
| Tidak ada pasangan wilayah tumpang tindih > 0,05 km² | poligon ganda / salah gambar |

- Satu transaksi: kalau ada yang `GAGAL`, **tidak ada yang berubah** (rollback) dan pesannya menunjuk masalahnya.
- Geometri tidak valid diperbaiki otomatis lalu dilaporkan di bagian `Info` — cek bentuknya di peta setelah itu.
- Berkas lain: `sh /seed/import_poligon.sh nama_berkas.geojson` (harus ada di `data/geojson/`).
- Format GeoJSON: tiap feature wajib punya `properties.id_polsek` (1–27) dan `properties.nama_polsek` yang sama dengan `data/bersih/polsek.csv`.
- Catatan data saat ini: 27 poligon bentuknya sederhana (7–37 titik per wilayah, cukup untuk peta zonasi). Ada satu "lubang" di tengah wilayah (kemungkinan kecamatan tanpa Polsek di data kita) dan Cimenyan terpisah dari yang lain — keduanya wajar.

## Mock Server (untuk Front End)

Front end bisa jalan **tanpa backend** memakai server tiruan yang mengikuti `docs/api-contract.md`:
```
cd mock-server
node server.js        # http://localhost:3000/api  (butuh Node.js >= 16, tanpa npm install)
```
Filter, paginasi, login (`admin`/`admin123`, `operator`/`operator123`), dan CRUD kasus berfungsi (disimpan di memori). Detail dan cara pakai file JSON statis: `data/mock/README.md`.
Saat backend asli siap, matikan mock server dan jalankan backend di port yang sama — front end tidak perlu diubah.

## Backend (FastAPI)

Detail lengkap: [`backend/README.md`](backend/README.md). Ringkasnya (PowerShell, database sudah menyala & terisi):
```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 3000
```
Cek: buka http://localhost:3000/api/health (harus `"status":"ok"`) dan http://localhost:3000/docs (dokumentasi interaktif).
Backend membaca `.env` di root repo (nilai `DB_*`). Port 3000 sama dengan mock server — jalankan salah satu saja.

## Cara Menjalankan (Ringkasan Development)

1. Clone repo: `git clone <url-repo>`
2. Salin `.env.example` menjadi `.env`, isi `DB_PASSWORD` (dan `DB_PORT` bila bukan 5432)
3. Database: **Setup Database** → **Migrasi** → **Impor Data** di atas
4. Backend: bagian **Backend (FastAPI)** di atas — atau pakai **Mock Server** bila backend belum siap
5. Front end: buka `frontend/` lewat Live Server (VS Code); API di `http://localhost:3000/api`

## Alur Kerja Git
- `main` selalu dalam kondisi bisa dijalankan; **jangan push langsung ke `main`**
- Buat branch per fitur: `feat/nama-fitur`, `fix/nama-bug`, `docs/nama-dokumen`
- Selesai -> buat Pull Request -> partner review -> merge
- Pesan commit: `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`
- Sebelum mulai kerja: `git pull origin main`
- Jangan commit `.env`, password, atau `node_modules`

## Dokumentasi
- API contract: `docs/api-contract.md` *(dilengkapi Minggu 1)*
- Timeline & to-do: lihat spreadsheet tim
