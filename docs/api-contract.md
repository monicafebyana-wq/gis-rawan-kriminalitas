# API Contract — Web GIS Rawan Kriminalitas

> **Status:** draft v1 — disepakati Monica & Dhea di Minggu 1. Kalau ada perubahan, edit file ini dulu, baru ubah kode.
> **Back end (Monica)** membuat API sesuai dokumen ini. **Front end (Dhea)** memakai data contoh di `data/mock/` sampai API siap, lalu tinggal ganti URL.

## 1. Aturan Umum

| Hal | Aturan |
|---|---|
| Base URL (dev) | `http://localhost:3000/api` |
| Format | JSON, UTF-8. Peta memakai **GeoJSON** (WGS 84 / EPSG:4326, urutan koordinat `[lng, lat]`) |
| Bahasa nama field | Indonesia, `snake_case` |
| Tahun | integer. Kalau `tahun` tidak dikirim → pakai tahun terbaru yang ada di DB (sekarang 2024) |
| Filter banyak nilai | dipisah koma, mis. `jenis=1,16` |
| Autentikasi | Endpoint publik: semua `GET`. Endpoint admin: header `Authorization: Bearer <token>` |
| CORS | Aktifkan untuk origin front end saat development |

### Aturan Zonasi (dihitung back end)
Berdasarkan **total semua jenis kejahatan** per Polsek pada tahun tsb:

| `kategori_zona` | Kriteria | Warna di peta (usulan) |
|---|---|---|
| `tinggi` | total >= 60 | merah `#FF3131` |
| `sedang` | 30 – 59 | kuning `#FFC800` |
| `rendah` | < 30 | hijau-tosca `#20A99B` |

**Keputusan penting:** ketika filter `jenis` dipakai, `total_kasus` mengikuti filter, tetapi `kategori_zona` **tetap** dari `total_semua_jenis`. Alasannya: ambang 60/30 dirancang untuk total semua jenis; kalau dihitung per jenis, hampir semua wilayah jadi "rendah".

### Format Error (semua endpoint)
```json
{ "error": { "kode": "VALIDASI_GAGAL", "pesan": "Parameter tahun harus berupa angka", "detail": ["tahun"] } }
```

| HTTP | `kode` | Kapan |
|---|---|---|
| 400 | `VALIDASI_GAGAL` | Parameter/body tidak valid |
| 401 | `TIDAK_TERAUTENTIKASI` | Token tidak ada/kedaluwarsa, atau login salah |
| 403 | `TIDAK_DIIZINKAN` | Peran tidak cukup |
| 404 | `TIDAK_DITEMUKAN` | ID tidak ada |
| 409 | `DATA_SUDAH_ADA` | Kombinasi polsek+jenis+tahun sudah ada |
| 500 | `KESALAHAN_SERVER` | Error tak terduga |

---

## 2. Endpoint Publik (dipakai peta & dashboard)

### 2.1 `GET /api/polsek` — Peta utama (GeoJSON)
Satu `Feature` per Polsek: poligon + jumlah kasus + zona. Ini endpoint yang menggambar peta.

| Query | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `tahun` | int | tidak | default tahun terbaru |
| `jenis` | id dipisah koma | tidak | filter jenis kejahatan; kosong = semua |
| `zona` | `tinggi`/`sedang`/`rendah` (koma) | tidak | tampilkan zona tertentu saja |
| `polsek` | id dipisah koma | tidak | batasi ke Polsek tertentu |

Respons `200` (contoh 1 dari 27 feature; koordinat dipersingkat):
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              107.4,
              -7.3
            ],
            [
              107.46000000000001,
              -7.3
            ],
            [
              107.46000000000001,
              -7.24
            ],
            [
              107.4,
              -7.24
            ],
            [
              107.4,
              -7.3
            ]
          ]
        ]
      },
      "properties": {
        "id_polsek": 1,
        "nama_polsek": "Bale Endah",
        "tahun": 2024,
        "total_kasus": 74,
        "total_semua_jenis": 74,
        "kategori_zona": "tinggi",
        "pusat": {
          "lat": -7.27,
          "lng": 107.43
        }
      }
    }
  ]
}
```
- `pusat` = titik tengah poligon (untuk heatmap & marker). Dihitung back end (`ST_PointOnSurface`).
- Contoh lengkap: `data/mock/polsek.json` (27 Polsek) dan `data/mock/polsek_filter_jenis_1_16.json` (hasil `?jenis=1,16`).
- ⚠️ Geometri di file mock adalah **kotak dummy**. Angka kasusnya asli dari CSV.

### 2.2 `GET /api/polsek/{id_polsek}` — Detail untuk popup
| Query | Tipe | Keterangan |
|---|---|---|
| `tahun` | int | default tahun terbaru |

Respons `200` (hanya jenis dengan jumlah > 0, urut terbanyak):
```json
{
  "id_polsek": 1,
  "nama_polsek": "Bale Endah",
  "tahun": 2024,
  "total_kasus": 74,
  "kategori_zona": "tinggi",
  "rincian_jenis": [
    {
      "id_jenis": 16,
      "kode_jenis": "KEROYOK",
      "nama_jenis": "Pengeroyokan",
      "jumlah": 17
    },
    {
      "id_jenis": 6,
      "kode_jenis": "CURANMOR_R2",
      "nama_jenis": "Curanmor Roda 2",
      "jumlah": 14
    },
    {
      "id_jenis": 4,
      "kode_jenis": "CURAT",
      "nama_jenis": "Pencurian dengan Pemberatan (Curat)",
      "jumlah": 11
    },
    {
      "id_jenis": 14,
      "kode_jenis": "SAJAM",
      "nama_jenis": "Senjata Tajam",
      "jumlah": 6
    },
    {
      "id_jenis": 2,
      "kode_jenis": "ANIAYA_BERAT",
      "nama_jenis": "Penganiayaan Berat",
      "jumlah": 5
    },
    {
      "id_jenis": 3,
      "kode_jenis": "CURAS",
      "nama_jenis": "Pencurian dengan Kekerasan (Curas)",
      "jumlah": 5
    },
    {
      "id_jenis": 11,
      "kode_jenis": "GELAP",
      "nama_jenis": "Penggelapan",
      "jumlah": 5
    },
    {
      "id_jenis": 18,
      "kode_jenis": "LAIN2",
      "nama_jenis": "Lain-lain",
      "jumlah": 5
    },
    {
      "id_jenis": 1,
      "kode_jenis": "ANIAYA",
      "nama_jenis": "Penganiayaan",
      "jumlah": 4
    },
    {
      "id_jenis": 8,
      "kode_jenis": "JUDI",
      "nama_jenis": "Perjudian",
      "jumlah": 1
    },
    {
      "id_jenis": 10,
      "kode_jenis": "TIPU",
      "nama_jenis": "Penipuan",
      "jumlah": 1
    }
  ]
}
```
File: `data/mock/polsek_detail_1.json`.

### 2.3 `GET /api/jenis` — Daftar jenis kejahatan (untuk dropdown filter)
Respons: `{ "data": [ { "id_jenis": 1, "kode_jenis": "ANIAYA", "nama_jenis": "Penganiayaan" }, ... ] }` — 18 item, lengkap di `data/mock/jenis.json`.

### 2.4 `GET /api/tahun` — Tahun yang tersedia (untuk filter periode)
Respons: `{ "data": [2024], "terbaru": 2024 }` — `data/mock/tahun.json`.

### 2.5 `GET /api/kasus` — Data tabel kasus (dengan paginasi)
| Query | Tipe | Keterangan |
|---|---|---|
| `tahun` | int | default tahun terbaru |
| `polsek` | id koma | filter Polsek |
| `jenis` | id koma | filter jenis |
| `page`, `limit` | int | default `1` dan `20` (maks `100`) |

Respons: `{ "page": 1, "limit": 20, "total_data": 486, "data": [ { "id_kasus": 1, "id_polsek": 1, "nama_polsek": "Bale Endah", "id_jenis": 1, "nama_jenis": "Penganiayaan", "tahun": 2024, "jumlah": 4 }, ... ] }` — `data/mock/kasus.json`.
(Catatan: `total_data` contoh 486 = jumlah baris di DB kalau semua kombinasi 27 x 18 disimpan; boleh hanya simpan yang jumlah > 0.)

### 2.6 `GET /api/statistik` — Dashboard (kartu & grafik batang)
| Query | Tipe | Keterangan |
|---|---|---|
| `tahun` | int | default tahun terbaru |
| `top` | int | jumlah jenis teratas di `top_jenis`, default `4` |

Respons `200` (ringkas):
```json
{
  "tahun": 2024,
  "total_kasus": 1163,
  "jumlah_polsek": 27,
  "jumlah_jenis": 18,
  "polsek_tertinggi": {
    "id_polsek": 5,
    "nama_polsek": "Cicalengka",
    "total_kasus": 76
  },
  "polsek_terendah": {
    "id_polsek": 19,
    "nama_polsek": "Nagreg",
    "total_kasus": 5
  },
  "distribusi_zona": {
    "tinggi": 10,
    "sedang": 7,
    "rendah": 10
  },
  "top_jenis": [
    {
      "id_jenis": 1,
      "kode_jenis": "ANIAYA",
      "nama_jenis": "Penganiayaan",
      "jumlah": 235
    },
    {
      "id_jenis": 16,
      "kode_jenis": "KEROYOK",
      "nama_jenis": "Pengeroyokan",
      "jumlah": 198
    },
    {
      "id_jenis": 6,
      "kode_jenis": "CURANMOR_R2",
      "nama_jenis": "Curanmor Roda 2",
      "jumlah": 154
    },
    {
      "id_jenis": 4,
      "kode_jenis": "CURAT",
      "nama_jenis": "Pencurian dengan Pemberatan (Curat)",
      "jumlah": 151
    }
  ],
  "persen_top_jenis": 63.5
}
```
Respons penuh juga memuat `per_polsek` (27 item, urut terbanyak → untuk grafik batang per Polsek) dan `per_jenis` (18 item → grafik per jenis). Lengkap di `data/mock/statistik.json`.

### 2.7 `GET /api/statistik/tren` — Grafik garis waktu
| Query | Tipe | Keterangan |
|---|---|---|
| `polsek` | id | opsional, kosong = seluruh wilayah |
| `jenis` | id koma | opsional |

Respons: `{ "data": [ { "tahun": 2024, "total_kasus": 1163 } ] }` — `data/mock/tren.json`.
⚠️ Data baru 2024 → tren hanya 1 titik. Struktur sudah siap multi-tahun; putuskan di Minggu 1 apakah akan menambah data tahun lain.

### 2.8 `GET /api/export` — Ekspor ringkasan
| Query | Tipe | Keterangan |
|---|---|---|
| `format` | `csv` (wajib) / `pdf` (opsional) | format berkas |
| `tahun`, `jenis`, `polsek` | sama seperti di atas | filter data yang diekspor |

Respons: berkas (`Content-Disposition: attachment`). Kolom CSV: `id_polsek, nama_polsek, tahun, total_kasus, kategori_zona`.

---

## 3. Endpoint Admin (butuh login)

### 3.1 `POST /api/auth/login`
Body: `{ "username": "admin", "password": "******" }`
Respons `200`: lihat `data/mock/login.json`. Error `401` kalau salah.
Simpan token di front end, kirim sebagai `Authorization: Bearer <token>`.

### 3.2 `GET /api/auth/me`
Respons: `{ "id_pengguna": 1, "username": "admin", "peran": "admin" }`

### 3.3 Peran

| Aksi | `operator` | `admin` |
|---|:-:|:-:|
| Lihat data (publik) | ✅ | ✅ |
| Tambah / ubah kasus, impor CSV | ✅ | ✅ |
| Hapus kasus | ❌ | ✅ |

### 3.4 CRUD kasus
| Method | Endpoint | Body | Respons |
|---|---|---|---|
| `POST` | `/api/kasus` | `{ "id_polsek": 1, "id_jenis": 1, "tahun": 2024, "jumlah": 4 }` | `201` objek kasus. `409` jika kombinasi sudah ada |
| `PUT` | `/api/kasus/{id_kasus}` | `{ "jumlah": 6 }` | `200` objek kasus terbaru |
| `DELETE` | `/api/kasus/{id_kasus}` | — | `204` (khusus `admin`) |

Setiap tambah/ubah/hapus/impor → back end **menghitung ulang** tabel `zona_kerawanan` untuk tahun terkait.

### 3.5 `POST /api/import/csv` — Impor rekap CSV
`multipart/form-data`:

| Field | Tipe | Keterangan |
|---|---|---|
| `file` | file `.csv` | format sama seperti `data/rekap_kriminalitas_2024.csv` (kolom: No, Polsek, 18 jenis, Jumlah) |
| `tahun` | int | wajib (CSV tidak punya kolom tahun) |
| `mode` | `tambah` / `timpa` | `timpa` = hapus data tahun tsb dulu. Default `timpa` |
| `dry_run` | bool | `true` = hanya validasi, tidak menyimpan |

Validasi: nama Polsek harus cocok dengan tabel `polsek`; angka >= 0; `Jumlah` = jumlah 18 kolom jenis.
Respons `200`:
```json
{ "tahun": 2024, "baris_dibaca": 27, "baris_valid": 27, "total_kasus": 1163, "peringatan": [], "disimpan": true }
```
Jika ada baris bermasalah → `400` dengan `detail` berisi nomor baris dan alasan.

---

## 4. Pemetaan Nama Jenis (CSV → `id_jenis`)

| id | kolom CSV | kode_jenis | nama_jenis |
|---|---|---|---|
| 1 | Aniaya | ANIAYA | Penganiayaan |
| 2 | Aniaya Berat | ANIAYA_BERAT | Penganiayaan Berat |
| 3 | Curas | CURAS | Pencurian dengan Kekerasan (Curas) |
| 4 | Curat | CURAT | Pencurian dengan Pemberatan (Curat) |
| 5 | Curanmor R4 | CURANMOR_R4 | Curanmor Roda 4 |
| 6 | Curanmor R2 | CURANMOR_R2 | Curanmor Roda 2 |
| 7 | Perkosaan | PERKOSAAN | Perkosaan |
| 8 | Judi | JUDI | Perjudian |
| 9 | Rusak | RUSAK | Perusakan |
| 10 | Tipu | TIPU | Penipuan |
| 11 | Gelap | GELAP | Penggelapan |
| 12 | Curi Biasa | CURI_BIASA | Pencurian Biasa |
| 13 | KDRT | KDRT | KDRT |
| 14 | Sajam | SAJAM | Senjata Tajam |
| 15 | Tdk Senang | TDK_SENANG | Perbuatan Tidak Menyenangkan |
| 16 | Keroyok | KEROYOK | Pengeroyokan |
| 17 | Cabul | CABUL | Pencabulan |
| 18 | Lain2 | LAIN2 | Lain-lain |

> Catatan: di slide, "Penganiayaan = 235" adalah kolom `Aniaya` saja (id 1); `Aniaya Berat` (39) dihitung terpisah.
> Nama Polsek di CSV berawalan "POLSEK" huruf besar (mis. `POLSEK BALE ENDAH`). Di DB/API disimpan sebagai `Bale Endah`; `id_polsek` = kolom `No` di CSV (1–27).

## 5. Checklist Kesepakatan (centang berdua)
- [ ] Nama & tipe field di atas sudah final
- [ ] Zona tetap dari `total_semua_jenis` saat ada filter jenis
- [ ] Putuskan: ada data tahun lain atau tren cukup 2024?
- [ ] Putuskan: ekspor `pdf` dibuat atau cukup `csv`?
- [ ] Back end: Node.js (Express) atau Laravel? (tidak mengubah contract ini)
