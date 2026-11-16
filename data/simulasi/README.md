# Data SIMULASI 2025–2026

> **Bukan data resmi kepolisian.** File di folder ini dibuat otomatis untuk pengembangan dan demo supaya fitur multi-tahun
> (filter tahun, tren, perbandingan, heatmap) bisa dicoba. Ganti dengan data resmi begitu tersedia.

| File | Isi |
|---|---|
| `Rekap_Data_Kriminalitas_2025.csv`, `Rekap_Data_Kriminalitas_2026.csv` | Rekap per Polsek x 18 jenis, **format sama** dengan `data/rekap_kriminalitas_2024.csv`. 2026 = periode Januari–Oktober. |
| `titik_simulasi_2024_2026.csv` | Satu baris per kasus (`lat,lng,jenis,tanggal,sumber,akurasi,polsek`), koordinat acak **di dalam poligon Polsek**. Jumlah per Polsek x jenis x tahun sama persis dengan rekapnya (2024 memakai jumlah asli). Semua bersumber `simulasi`. |

Dibuat oleh `data/scripts/simulasi_2025_2026.py` (seed tetap, hasil selalu sama):
`pip install shapely && python data/scripts/simulasi_2025_2026.py`

Aturan: jumlah 2025 per Polsek x jenis = Poisson(jumlah 2024 x tren Polsek), tren rata-rata +4%; 2026 melanjutkan tren (+2%) tapi hanya 10 bulan.

## Cara memasukkan ke sistem
```
# 1) migrasi 006 (catatan_tahun + kolom sumber_data), sekali saja
docker exec gis_kriminalitas_db sh /migrations/run.sh

# 2) rekap: halaman Kelola Data -> Impor CSV (tahun 2025, lalu 2026), atau API:
POST /api/import/csv   file=Rekap_Data_Kriminalitas_2025.csv  tahun=2025  mode=timpa

# 3) titik simulasi (untuk heatmap): halaman Titik Kejadian -> Impor CSV (klik "Periksa dulu" dulu)
#    Kalau sebelumnya sudah mengimpor titik simulasi lama, hapus dulu agar tidak dobel:
#    DELETE FROM titik_kejadian WHERE sumber_data = 'simulasi';
```
Migrasi 006 otomatis memberi **catatan tahun** untuk 2025 dan 2026 ("data simulasi") yang tampil sebagai peringatan di Peta dan Dashboard.
Setelah data resmi masuk: Master Data -> Catatan tahun -> Hapus.
