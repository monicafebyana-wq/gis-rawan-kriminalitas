# API Contract (draft — sepakati berdua di Minggu 1)

| Method | Endpoint | Query | Respons |
|--------|----------|-------|---------|
| GET | /api/polsek | jenis, tahun | GeoJSON FeatureCollection (properties: id_polsek, nama_polsek, total_kasus, kategori_zona) |
| GET | /api/kasus | polsek, jenis, tahun | JSON array rincian kasus |
| GET | /api/statistik | tahun | JSON ringkasan (total, top jenis, distribusi) |
| POST | /api/auth/login | - | token |

Contoh respons: tambahkan di `data/mock/`.
