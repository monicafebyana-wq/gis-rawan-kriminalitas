# Laporan Validasi Data Kriminalitas 2024

Sumber: `data/rekap_kriminalitas_2024.csv`

## Hasil Pengecekan

| Status | Pengecekan | Keterangan |
|---|---|---|
| LULUS | Jumlah baris Polsek = 27 | ditemukan 27 |
| LULUS | 18 kolom jenis kejahatan ada lengkap |  |
| LULUS | Tidak ada kolom tak dikenal |  |
| LULUS | Semua angka valid (bilangan bulat >= 0, tidak kosong) |  |
| LULUS | Nama Polsek unik (tanpa duplikat) |  |
| LULUS | Kolom No berurutan 1..27 (dipakai sebagai id_polsek) |  |
| LULUS | Tidak ada spasi nyasar di nama asli | 0 baris dirapikan |
| LULUS | Kolom Jumlah = jumlah 18 kolom jenis di setiap baris |  |
| LULUS | Total seluruh kasus = 1.163 | hasil 1163 |
| LULUS | Tabel kasus_kejahatan = 27 x 18 = 486 baris, total tetap 1.163 | 486 baris, total 1163 |

## Normalisasi Nama Polsek

Aturan: buang awalan `POLSEK`, rapikan spasi, ubah ke huruf kapital di awal kata.

| id_polsek | Nama asli di CSV | Nama setelah normalisasi | Total kasus | Zona |
|---|---|---|---|---|
| 1 | POLSEK BALE ENDAH | Bale Endah | 74 | tinggi |
| 2 | POLSEK BANJARAN | Banjaran | 65 | tinggi |
| 3 | POLSEK BOJONG SOANG | Bojong Soang | 23 | rendah |
| 4 | POLSEK CANGKUANG | Cangkuang | 69 | tinggi |
| 5 | POLSEK CICALENGKA | Cicalengka | 76 | tinggi |
| 6 | POLSEK CIKANCUNG | Cikancung | 34 | sedang |
| 7 | POLSEK CILEUNYI | Cileunyi | 64 | tinggi |
| 8 | POLSEK CIMAUNG | Cimaung | 17 | rendah |
| 9 | POLSEK CIMENYAN | Cimenyan | 26 | rendah |
| 10 | POLSEK CIPARAY | Ciparay | 63 | tinggi |
| 11 | POLSEK CIWIDEY | Ciwidey | 31 | sedang |
| 12 | POLSEK DAYEUH KOLOT | Dayeuh Kolot | 42 | sedang |
| 13 | POLSEK IBUN | Ibun | 17 | rendah |
| 14 | POLSEK KATAPANG | Katapang | 61 | tinggi |
| 15 | POLSEK KERTASARI | Kertasari | 23 | rendah |
| 16 | POLSEK MAJALAYA | Majalaya | 52 | sedang |
| 17 | POLSEK MARGAASIH | Margaasih | 64 | tinggi |
| 18 | POLSEK MARGAHAYU | Margahayu | 26 | rendah |
| 19 | POLSEK NAGREG | Nagreg | 5 | rendah |
| 20 | POLSEK PACET | Pacet | 66 | tinggi |
| 21 | POLSEK PANGALENGAN | Pangalengan | 16 | rendah |
| 22 | POLSEK PASEH | Paseh | 20 | rendah |
| 23 | POLSEK PASIR JAMBU | Pasir Jambu | 9 | rendah |
| 24 | POLSEK PEMEUGPEUK | Pameungpeuk | 48 | sedang |
| 25 | POLSEK RANCAEKEK | Rancaekek | 59 | sedang |
| 26 | POLSEK SOLOKAN JERUK | Solokan Jeruk | 38 | sedang |
| 27 | POLSEK SOREANG | Soreang | 75 | tinggi |

## Koreksi Salah Ketik

- `Pemeugpeuk` → `Pameungpeuk` (sumber CSV: salah ketik)

## Catatan Pencocokan Poligon

Kolom `nama_wilayah_resmi` di `polsek.csv` adalah USULAN nama kecamatan resmi untuk join dengan GeoJSON. Cek ulang terhadap atribut nama di data BIG/OSM yang dipakai.

Yang berbeda dari nama Polsek: Bale Endah → Baleendah, Bojong Soang → Bojongsoang, Dayeuh Kolot → Dayeuhkolot, Pasir Jambu → Pasirjambu

## Ringkasan

- Polsek: 27 · Jenis: 18 · Total kasus: 1163
- Distribusi zona (>=60 tinggi, 30-59 sedang, <30 rendah): tinggi 10, sedang 7, rendah 10

## Peringatan (tidak fatal)

- Jenis dengan total 0 sepanjang 2024: Perkosaan (tetap disimpan; jumlah = 0).

## Berkas Hasil (`data/bersih/`)

- `polsek.csv` → tabel `polsek` (tanpa kolom `geom`, diisi dari GeoJSON nanti; kolom `nama_wilayah_resmi` untuk join poligon)
- `jenis_kejahatan.csv` → tabel `jenis_kejahatan`
- `kasus_kejahatan.csv` → tabel `kasus_kejahatan` (486 baris, termasuk jumlah 0)
- `rekap_2024_bersih.csv` → versi lebar untuk dicek manual / uji data spasial
