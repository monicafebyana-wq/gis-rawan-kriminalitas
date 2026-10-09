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
- **Back end:** Node.js (Express) *atau* Laravel — *(isi sesuai keputusan tim)*
- **Database:** PostgreSQL + PostGIS
- **Data:** CSV (atribut kriminalitas), GeoJSON WGS 84 (batas wilayah)

## Struktur Repo
```
backend/      # REST API, autentikasi, impor CSV, perhitungan zonasi
frontend/     # UI, peta Leaflet, dashboard
data/         # CSV sumber, GeoJSON wilayah
  mock/       # data contoh sesuai API contract (untuk frontend)
docs/         # API contract, wireframe, laporan
```

## Pembagian Peran
| Area | PIC |
|------|-----|
| Data, database, API, zonasi, autentikasi, deploy | Monica |
| Data spasial, UI, peta, filter, dashboard | Dhea |
| API contract, pengujian, dokumentasi, demo | Berdua |

## Cara Menjalankan (Development)
> Lengkapi seiring pengerjaan.

1. Clone repo: `git clone <url-repo>`
2. Salin `.env.example` menjadi `.env` lalu isi sesuai lingkungan masing-masing
3. Setup PostgreSQL + PostGIS *(langkah ditambahkan Minggu 1)*
4. Jalankan backend: *(TBD)*
5. Buka frontend: *(TBD)*

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
