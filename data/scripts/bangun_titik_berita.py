"""Bangun data/berita/titik_berita_2025_2026.csv: kejadian kriminal NYATA di Kabupaten Bandung yang diberitakan media,
siap diimpor lewat halaman Titik Kejadian (kolom sumber=berita, akurasi=kecamatan).

Cara membuat (dari root repo):   pip install shapely   &&   python data/scripts/bangun_titik_berita.py

CATATAN PENTING
* Daftar di bawah dikurasi manual dari pemberitaan media nasional/regional (kunjungan 15 Nov 2026). Judul dan ringkasan DITULIS ULANG
  dengan kalimat sendiri; hanya tautan, nama media, dan tanggal yang diambil dari sumber. Isi artikel tidak disalin.
* Koordinat BUKAN lokasi TKP. Berita hanya menyebut kecamatan/desa, jadi marker diletakkan di dalam poligon Polsek yang menangani
  (akurasi='kecamatan'), digeser sedikit supaya tidak bertumpuk. Jangan dipakai untuk analisis lokasi persis.
* tanggal = tanggal kejadian bila disebut di berita; jika tidak disebut, tanggal berita/pengungkapan (ditandai di ringkasan).
* Klasifikasi jenis dilakukan penyusun berdasarkan uraian berita (18 jenis baku proyek ini; pembunuhan dan narkoba/obat keras masuk LAIN2),
  BUKAN klasifikasi resmi kepolisian. Perhatikan: GELAP = Penggelapan.
* Kasus kekerasan seksual dan kasus yang melibatkan anak sengaja TIDAK dimasukkan.
* Tambahkan kasus baru dengan menambah dict di BERITA, lalu jalankan ulang skrip ini.
"""
import csv
import json
import math
import random
from pathlib import Path

from shapely.geometry import Point, shape

DATA = Path(__file__).resolve().parents[1]

# polsek: nama sesuai tabel polsek (data/bersih/polsek.csv). tgl_berita boleh kosong.
BERITA = [
    dict(tgl="2025-02-13", jenis="CURANMOR_R2", polsek="Cileunyi", sumber="JPNN (ANTARA)", tgl_berita="2025-02-13",
         url="https://www.jpnn.com/news/viral-maling-motor-terjebak-di-plafon-begini-ceritanya",
         judul="Pencuri motor terjebak di plafon rumah warga di Cinunuk, Cileunyi",
         ringkasan="Pelaku pencurian motor dipergoki warga Kp. Cipondoh, Desa Cinunuk, lalu kabur ke atap dan terjebak di plafon sebelum diamankan petugas."),
    dict(tgl="2025-03-16", jenis="SAJAM", polsek="Soreang", sumber="detikJabar", tgl_berita="",
         url="https://www.detik.com/jabar/hukum-dan-kriminal/d-7826539/viral-pria-di-bandung-palak-warga-sambil-acungkan-golok",
         judul="Pria memalak warga sambil mengacungkan golok di Soreang",
         ringkasan="Aksi pemalakan di Jl. Gading Tutuka, Desa Cingcin, terekam video dan viral. Pelaku ditangkap di kontrakannya pada malam yang sama."),
    dict(tgl="2025-03-17", jenis="KEROYOK", polsek="Cimaung", sumber="detikJabar", tgl_berita="2025-03-17",
         url="https://www.detik.com/jabar/hukum-dan-kriminal/d-7827026/satu-pengeroyok-jukir-di-minimarket-bandung-ditangkap",
         judul="Anggota geng motor pengeroyok juru parkir minimarket di Cimaung ditangkap",
         ringkasan="Polresta Bandung mengamankan satu pelaku pengeroyokan juru parkir sebuah minimarket dalam waktu sekitar tiga jam. Tanggal = tanggal rilis berita."),
    dict(tgl="2025-05-29", jenis="LAIN2", polsek="Ciwidey", sumber="detikJabar", tgl_berita="2025-05-29",
         url="https://www.detik.com/jabar/hukum-dan-kriminal/d-7938879/cemburu-buta-pria-di-ciwidey-tikam-petani-hingga-tewas",
         judul="Petani tewas ditikam di wilayah Ciwidey, pelaku tertangkap empat jam kemudian",
         ringkasan="Kasus pembunuhan di Kp. Cikareo, Desa Alam Endah (Kec. Rancabali, wilayah Polsek Ciwidey) dengan motif dugaan perselingkuhan. Tanggal = tanggal berita."),
    dict(tgl="2025-06-15", jenis="CURAT", polsek="Pameungpeuk", sumber="iNews", tgl_berita="2025-06-15",
         url="https://www.inews.id/regional/jabar/2-pencuri-gagal-gasak-motor-di-arjasari-bandung-1-pelaku-tercebur-ke-sungai",
         judul="Dua pencuri gagal membawa kabur motor di Arjasari, satu pelaku tercebur ke sungai",
         ringkasan="Pencurian dengan pemberatan di Kp. Sukatinggal, Desa Patrolsari (Kec. Arjasari), ditangani Polsek Pameungpeuk. Motor ditinggalkan, uang tunai Rp21 juta dilaporkan hilang."),
    dict(tgl="2025-11-27", jenis="RUSAK", polsek="Pangalengan", sumber="Republika", tgl_berita="",
         url="https://rejabar.republika.co.id/berita/toezig282/polemik-perusakan-ribuan-pohon-teh-di-pangalengan-bandung-ptpn-minta-kepastian-hukum-untuk-pelaku",
         judul="Perusakan ribuan tanaman teh di perkebunan Malabar, Pangalengan",
         ringkasan="Sekitar 4.500 tanaman teh PTPN dirusak; perusahaan menempuh jalur hukum dan pekerjanya diduga dianiaya. Tanggal = tanggal olah TKP polisi (27/11/2025)."),
    dict(tgl="2025-12-22", jenis="LAIN2", polsek="Rancaekek", sumber="detikJabar", tgl_berita="2025-12-23",
         url="https://www.detik.com/jabar/hukum-dan-kriminal/d-8273229/usai-nonton-hiburan-pria-di-rancaekek-tewas-ditusuk",
         judul="Pria tewas ditusuk di bantaran sungai Cimande, Rancaekek",
         ringkasan="Korban ditemukan bersimbah darah di Kp. Jelegong, Desa Sukamulya, setelah menonton hiburan. Polisi melakukan olah TKP dan memburu pelaku."),
    dict(tgl="2026-04-23", jenis="CURAS", polsek="Pangalengan", sumber="JPNN", tgl_berita="",
         url="https://www.jpnn.com/news/perampokan-di-pangalengan-ibu-anak-disekap-emas-hingga-perhiasan-dibawa-kabur",
         judul="Perampokan dan penyekapan di rumah warga Pangalengan, emas dan motor dibawa kabur",
         ringkasan="Perampok menyekap dua penghuni rumah di Kp. Padawaas, Desa Margamulya, pada dini hari Kamis 23/4 lalu membawa emas, perhiasan, dan sepeda motor."),
    dict(tgl="2026-07-08", jenis="SAJAM", polsek="Bale Endah", sumber="RRI", tgl_berita="2026-07-10",
         url="https://rri.co.id/bandung/kriminalitas/2558533/polresta-bandung-cokok-kelompok-lapetre-bersenjata-tajam-di-rancamanyar",
         judul="Polisi menangkap kelompok remaja bersenjata tajam yang meresahkan warga Rancamanyar",
         ringkasan="Video kelompok remaja membawa senjata tajam di Desa Rancamanyar beredar di media sosial; Polresta Bandung dan Polsek Baleendah bergerak menindaklanjuti."),
    dict(tgl="2026-07-12", jenis="CURAS", polsek="Bojong Soang", sumber="RRI", tgl_berita="2026-07-13",
         url="https://rri.co.id/bandung/kriminalitas/2565463/belasan-orang-diciduk-polisi-usai-rampas-motor-di-bojongsoang",
         judul="Belasan orang diamankan setelah perampasan motor seorang remaja di Jalan Raya Bojongsoang",
         ringkasan="Kejadian dini hari 12 Juli 2026; lima orang diamankan beberapa jam kemudian dan total 15 orang diamankan setelah pengembangan."),
    dict(tgl="2026-07-18", jenis="CURAS", polsek="Majalaya", sumber="RRI", tgl_berita="2026-07-28",
         url="https://rri.co.id/bandung/hukum/kriminalitas/2606243/sempat-buron-pelaku-curas-di-majalaya-dicokok-polisi",
         judul="Pelaku pencurian dengan kekerasan terhadap buruh pabrik di Majalaya ditangkap",
         ringkasan="Kejadian pagi hari di Kp. Rancajigang, Desa Padamulya; pelaku sempat buron dan ditangkap tim gabungan pada 28 Juli 2026."),
    dict(tgl="2026-07-30", jenis="LAIN2", polsek="Cicalengka", sumber="ANTARA", tgl_berita="2026-07-30",
         url="https://www.antaranews.com/berita/5672789/polresta-bandung-bongkar-rumah-yang-simpan-784500-butir-obat-keras",
         judul="Polresta Bandung membongkar rumah penyimpan ratusan ribu butir obat keras di Cicalengka",
         ringkasan="Satresnarkoba menemukan 784.500 butir obat keras terlarang di sebuah rumah di Perum Buana Cicalengka. Diklasifikasikan Lain-lain (tidak ada jenis narkoba di 18 jenis). Tanggal = tanggal pengungkapan."),
    dict(tgl="2026-08-18", jenis="ANIAYA", polsek="Cicalengka", sumber="ANTARA", tgl_berita="2026-08-18",
         url="https://www.antaranews.com/berita/5699696/polresta-bandung-ringkus-terduga-pelaku-pemukulan-kapolsek-cicalengka",
         judul="Terduga pelaku pemukulan Kapolsek dan Danramil Cicalengka diringkus",
         ringkasan="Keributan terjadi saat pengamanan karnaval HUT ke-81 RI dan petugas yang melerai dipukul. Tanggal = tanggal rilis penangkapan."),
    dict(tgl="2026-08-26", jenis="CURAS", polsek="Margaasih", sumber="detikJabar", tgl_berita="2026-08-30",
         url="https://www.detik.com/jabar/berita/d-8640631/bandung-raya-sepekan-teror-buas-pitbull",
         judul="Mahasiswi menjadi korban penjambretan di Margaasih",
         ringkasan="Penjambretan terjadi Rabu petang 26 Agustus 2026; dimuat dalam rangkuman berita pekanan Bandung Raya."),
    dict(tgl="2026-10-07", jenis="CURAT", polsek="Cicalengka", sumber="ANTARA", tgl_berita="2026-10-07",
         url="https://www.antaranews.com/berita/5775536/polisi-amankan-dua-terduga-pencuri-kabel-menara-seluler-di-cicalengka",
         judul="Dua terduga pencuri kabel menara seluler diamankan di Cicalengka",
         ringkasan="Pencurian kabel menara provider di Kp. Balong, Desa Waluya; dua pelaku diamankan Polsek Cicalengka."),
    dict(tgl="2026-10-11", jenis="CURAS", polsek="Nagreg", sumber="JPNN", tgl_berita="",
         url="https://www.jpnn.com/news/3-begal-ini-mengaku-polisi-saat-beraksi-di-kabupaten-bandung",
         judul="Tiga begal yang mengaku polisi di Nagreg tertangkap sehari setelah korban melapor",
         ringkasan="Kejadian dini hari Minggu 11/10/2026: motor dan ponsel korban dirampas; pelaku ditangkap setelah laporan di Polsek Nagreg pada 12/10."),
]


def main() -> None:
    geo = json.load(open(DATA / "geojson" / "polsek_poligon.geojson", encoding="utf-8"))
    poligon = {f["properties"]["nama_polsek"]: shape(f["geometry"]) for f in geo["features"]}
    rng = random.Random(7)
    terpakai: dict[str, int] = {}
    baris = []
    for b in BERITA:
        g = poligon[b["polsek"]]
        dalam = g.buffer(-0.0015) if not g.buffer(-0.0015).is_empty else g
        pusat = dalam.representative_point()
        n = terpakai.get(b["polsek"], 0)
        terpakai[b["polsek"]] = n + 1
        titik = pusat
        if n:                                                      # kasus ke-2, ke-3 di Polsek yang sama: geser <= ~1,3 km, tetap di dalam poligon
            for _ in range(500):
                r, a = rng.uniform(0.004, 0.012), rng.uniform(0, 2 * math.pi)
                kandidat = Point(pusat.x + r * math.cos(a), pusat.y + r * math.sin(a))
                if dalam.contains(kandidat):
                    titik = kandidat
                    break
        baris.append([round(titik.y, 6), round(titik.x, 6), b["jenis"], b["tgl"], "berita", "kecamatan", b["polsek"],
                      b["judul"], b["sumber"], b["url"], b["tgl_berita"], b["ringkasan"]])
    baris.sort(key=lambda r: r[3])
    out = DATA / "berita" / "titik_berita_2025_2026.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lng", "jenis", "tanggal", "sumber", "akurasi", "polsek", "judul_berita", "sumber_berita", "url_berita", "tanggal_berita", "ringkasan"])
        w.writerows(baris)
    print(f"{len(baris)} titik berita -> {out}")


if __name__ == "__main__":
    main()
