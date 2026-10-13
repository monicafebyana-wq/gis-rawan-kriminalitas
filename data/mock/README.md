# Data Mock (untuk Front End)

Semua angka kasus berasal dari data asli (`data/bersih/`). **Geometri poligon di `polsek*.json` adalah kotak DUMMY** sampai GeoJSON asli siap.

## Dua cara memakai

### 1. Mock server (disarankan — filter & paginasi berfungsi)
```
cd mock-server
node server.js          # atau: npm start   (butuh Node.js >= 16, tanpa npm install)
```
Jalan di `http://localhost:3000/api` — sama dengan base URL backend asli, jadi **kode front end tidak perlu diubah** saat pindah ke backend sungguhan. Ganti port dengan `PORT=3001 node server.js` (PowerShell: `$env:PORT=3001; node server.js`).

Akun uji: `admin` / `admin123` (peran admin) · `operator` / `operator123` (peran operator).
Token dikirim sebagai `Authorization: Bearer <token>` (token dari respons login).
Perubahan lewat POST/PUT/DELETE tersimpan di memori saja dan hilang saat server restart (atau panggil `POST /api/_reset`).

Pakai poligon asli: taruh file di `data/geojson/` dengan nama `polsek.geojson` atau `polsek_poligon.geojson` (FeatureCollection; tiap feature wajib punya `properties.id_polsek` 1–27, lihat `data/bersih/polsek.csv`), lalu restart server.

### 2. File JSON statis (tanpa Node)
Buka halaman lewat server statis (mis. ekstensi **Live Server** di VS Code); `fetch()` ke file:// tidak jalan di browser. Pemetaan endpoint → file:

| Endpoint | File |
|---|---|
| `GET /api/polsek` | `polsek.json` |
| `GET /api/polsek?jenis=1,16` | `polsek_filter_jenis_1_16.json` |
| `GET /api/polsek/{id}` | `polsek_detail_{id}.json` (id 1–27) |
| `GET /api/jenis` | `jenis.json` |
| `GET /api/tahun` | `tahun.json` |
| `GET /api/kasus` (halaman 1, limit 20) | `kasus.json` |
| `GET /api/statistik` | `statistik.json` |
| `GET /api/statistik/tren` | `tren.json` |
| `POST /api/auth/login` | `login.json` |
| `GET /api/auth/me` | `me.json` |
| `POST /api/import/csv` | `import_csv.json` |
| Respons error | `error_400.json`, `error_401.json`, `error_404.json` |

Filter lain (selain `jenis=1,16`) tidak tersedia di mode statis — pakai mock server.

## Tips di front end
Simpan base URL di satu tempat supaya mudah pindah ke backend asli:
```js
const API_BASE = 'http://localhost:3000/api';
const WARNA = { tinggi: '#FF3131', sedang: '#FFC800', rendah: '#20A99B' };
const res = await fetch(`${API_BASE}/polsek?tahun=2024&jenis=1,16`);
const geojson = await res.json();            // FeatureCollection
L.geoJSON(geojson, {
  style: f => ({ fillColor: WARNA[f.properties.kategori_zona], fillOpacity: 0.6, weight: 1 })
}).addTo(map);
```
