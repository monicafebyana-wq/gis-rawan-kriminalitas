# Titik kejadian yang dilengkapi berita

`titik_berita_2025_2026.csv` berisi **kejadian kriminal nyata** di Kabupaten Bandung yang diberitakan media pada 2025–2026,
masing-masing dengan tautan berita. Dibangun oleh `data/scripts/bangun_titik_berita.py` (daftar kejadiannya ada di dalam skrip,
mudah ditambah).

## Yang perlu diketahui
- **Lokasi marker = perkiraan.** Berita biasanya hanya menyebut kecamatan/desa, jadi marker diletakkan di dalam poligon Polsek yang
  menangani (`akurasi = kecamatan`) dan digeser sedikit agar tidak bertumpuk. Peta menampilkan catatan ini di popup.
- **Tidak semua kasus ada beritanya.** Hanya kasus yang diliput media. Karena itu lapisan berita terpisah dari rekap dan heatmap.
- Judul dan ringkasan ditulis ulang dengan kalimat sendiri; hanya tautan, nama media, dan tanggal yang diambil dari sumber.
  Isi artikel tidak disalin.
- `tanggal` = tanggal kejadian bila disebut; kalau tidak, tanggal berita/pengungkapan (dijelaskan di ringkasan).
- Klasifikasi jenis dilakukan penyusun dari uraian berita, **bukan klasifikasi resmi polisi**. Pembunuhan dan narkoba/obat keras
  masuk `LAIN2` karena tidak ada di 18 jenis baku. (`GELAP` = Penggelapan.)
- Kasus kekerasan seksual dan yang melibatkan anak sengaja tidak dimasukkan.
- Tautan bisa mati atau berubah di kemudian hari; periksa sebelum dipresentasikan.

## Cara memasukkan
Halaman **Titik Kejadian -> Impor titik dari CSV** (klik "Periksa dulu", lalu "Simpan"), atau `POST /api/titik/import`.
Kolom berita yang didukung: `sumber, akurasi, polsek, judul_berita, sumber_berita, url_berita, tanggal_berita, ringkasan`.
Lalu di Peta nyalakan **Kejadian dengan berita**.
