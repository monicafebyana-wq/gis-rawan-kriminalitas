"""Baca + validasi CSV titik kejadian.

Kolom WAJIB (nama tidak peka huruf besar/kecil):
  lat | latitude | lintang,  lng | lon | longitude | bujur,
  jenis | kode_jenis | id_jenis (isi: kode seperti CURAT, nama jenis, atau id),  tanggal | tgl | date (YYYY-MM-DD atau DD/MM/YYYY)
Kolom OPSIONAL:
  sumber   laporan (default) | berita | simulasi
  akurasi  tepat (default) | desa | kecamatan   (isi 'kecamatan' bila koordinat hanya perkiraan wilayah)
  polsek   nama Polsek; kalau diisi, dipakai sebagai id_polsek (kalau kosong: otomatis dari poligon wilayah)
  judul_berita, sumber_berita, url_berita, tanggal_berita, ringkasan   -> melengkapi titik dengan satu berita
           (url_berita diisi => judul_berita dan sumber_berita wajib; url harus http/https)
Pemisah , atau ; (bila ; maka koma dibaca sebagai desimal). BOM Excel didukung. Maks 5 MB / 20.000 baris."""
import csv
import io
import math
import re
from datetime import date, datetime

from app.errors import validasi_gagal
from app.services.geojson_polsek import BATAS_WILAYAH
from app.services.impor_csv import normalkan_nama

MAKS_BYTE = 5 * 1024 * 1024
MAKS_BARIS = 20_000
MAKS_ERROR_DITAMPILKAN = 50
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
SUMBER_BOLEH = ("laporan", "berita", "simulasi")
AKURASI_BOLEH = ("tepat", "desa", "kecamatan")
POLA_URL = re.compile(r"^https?://\S+$", re.I)
MAKS_JUDUL, MAKS_SUMBER_BERITA, MAKS_URL, MAKS_RINGKASAN = 300, 100, 2000, 600

_ALIAS = {"lat": ("lat", "latitude", "lintang"), "lng": ("lng", "lon", "long", "longitude", "bujur"),
          "jenis": ("jenis", "kode_jenis", "id_jenis"), "tanggal": ("tanggal", "tgl", "date")}
_OPSIONAL = {"sumber": ("sumber", "sumber_data"), "akurasi": ("akurasi",), "polsek": ("polsek", "nama_polsek"),
             "judul": ("judul_berita",), "sumber_berita": ("sumber_berita",), "url": ("url_berita",),
             "tanggal_berita": ("tanggal_berita",), "ringkasan": ("ringkasan", "ringkasan_berita")}


def parse_tanggal(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def baca_csv(isi: bytes, jenis_db: dict[str, int], polsek_db: dict[str, int] | None = None) -> list[dict]:
    """jenis_db: {KODE huruf besar | nama huruf kecil | id sebagai teks: id_jenis}.  polsek_db: {nama_polsek huruf kecil: id_polsek}.
    Tiap baris hasil: {lat, lng, id_jenis, tanggal, sumber, akurasi, id_polsek (atau None), berita (dict atau None)}."""
    polsek_db = polsek_db or {}
    if len(isi) > MAKS_BYTE:
        raise validasi_gagal(f"Berkas terlalu besar (maksimal {MAKS_BYTE // 1024 // 1024} MB)", ["file"])
    try:
        teks = isi.decode("utf-8-sig")
    except UnicodeDecodeError:
        teks = isi.decode("cp1252", errors="replace")
    baris_teks = teks.splitlines()
    if not baris_teks or not baris_teks[0].strip():
        raise validasi_gagal("Berkas kosong", ["file"])
    pemisah = ";" if baris_teks[0].count(";") > baris_teks[0].count(",") else ","
    rows = list(csv.reader(io.StringIO(teks), delimiter=pemisah))
    idx = {h.strip().lower(): i for i, h in enumerate(rows[0])}
    kol = {k: next((idx[a] for a in alias if a in idx), None) for k, alias in _ALIAS.items()}
    hilang = [k for k, v in kol.items() if v is None]
    if hilang:
        raise validasi_gagal("Format kolom CSV tidak sesuai", [f"Kolom tidak ditemukan: {', '.join(hilang)} (lihat README: Titik kejadian)"])
    opsi = {k: next((idx[a] for a in alias if a in idx), None) for k, alias in _OPSIONAL.items()}
    if len(rows) - 1 > MAKS_BARIS:
        raise validasi_gagal(f"Terlalu banyak baris (maksimal {MAKS_BARIS})", ["file"])

    x0, y0, x1, y1 = BATAS_WILAYAH
    errors: list[str] = []
    hasil: list[dict] = []
    for no, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        sel = {k: (r[i].strip() if i < len(r) else "") for k, i in kol.items()}
        ops = {k: ((r[i].strip() if i < len(r) else "") if i is not None else "") for k, i in opsi.items()}
        masalah = []
        try:
            lat = float(sel["lat"].replace(",", ".") if pemisah == ";" else sel["lat"])
            lng = float(sel["lng"].replace(",", ".") if pemisah == ";" else sel["lng"])
            if not (math.isfinite(lat) and math.isfinite(lng)):
                raise ValueError
            if not (x0 <= lng <= x1 and y0 <= lat <= y1):
                masalah.append(f"koordinat ({lat}, {lng}) di luar kotak wilayah - lat/lng tertukar?")
        except ValueError:
            masalah.append(f"lat/lng bukan angka (isi: '{sel['lat']}', '{sel['lng']}')")
            lat = lng = None
        id_jenis = jenis_db.get(sel["jenis"].upper()) or jenis_db.get(sel["jenis"].lower()) or jenis_db.get(sel["jenis"])
        if id_jenis is None:
            masalah.append(f"jenis '{sel['jenis']}' tidak dikenal")
        tgl = parse_tanggal(sel["tanggal"])
        if tgl is None or not (TGL_MIN <= tgl <= TGL_MAX):
            masalah.append(f"tanggal '{sel['tanggal']}' tidak valid (pakai YYYY-MM-DD)")

        sumber = (ops["sumber"] or "laporan").lower()
        if sumber not in SUMBER_BOLEH:
            masalah.append(f"sumber '{ops['sumber']}' tidak dikenal (pilih: {', '.join(SUMBER_BOLEH)})")
        akurasi = (ops["akurasi"] or "tepat").lower()
        if akurasi not in AKURASI_BOLEH:
            masalah.append(f"akurasi '{ops['akurasi']}' tidak dikenal (pilih: {', '.join(AKURASI_BOLEH)})")
        id_polsek = None
        if ops["polsek"]:
            id_polsek = polsek_db.get(normalkan_nama(ops["polsek"]).lower())
            if id_polsek is None:
                masalah.append(f"polsek '{ops['polsek']}' tidak dikenal")

        berita = None
        if ops["url"] or ops["judul"] or ops["sumber_berita"]:
            if not POLA_URL.match(ops["url"]) or len(ops["url"]) > MAKS_URL:
                masalah.append("url_berita harus diawali http:// atau https:// (maks. 2000 karakter)")
            if not ops["judul"] or len(ops["judul"]) > MAKS_JUDUL:
                masalah.append(f"judul_berita wajib diisi (maks. {MAKS_JUDUL} karakter)")
            if not ops["sumber_berita"] or len(ops["sumber_berita"]) > MAKS_SUMBER_BERITA:
                masalah.append(f"sumber_berita wajib diisi (maks. {MAKS_SUMBER_BERITA} karakter)")
            if len(ops["ringkasan"]) > MAKS_RINGKASAN:
                masalah.append(f"ringkasan maksimal {MAKS_RINGKASAN} karakter")
            tgl_berita = parse_tanggal(ops["tanggal_berita"]) if ops["tanggal_berita"] else None
            if ops["tanggal_berita"] and tgl_berita is None:
                masalah.append(f"tanggal_berita '{ops['tanggal_berita']}' tidak valid (pakai YYYY-MM-DD)")
            berita = {"judul": ops["judul"], "sumber": ops["sumber_berita"], "url": ops["url"],
                      "tanggal_terbit": tgl_berita, "ringkasan": ops["ringkasan"] or None}
        if sumber == "berita" and berita is None:
            masalah.append("sumber 'berita' wajib disertai url_berita, judul_berita, dan sumber_berita")

        if masalah:
            errors.append(f"baris {no}: " + "; ".join(masalah))
        else:
            hasil.append({"lat": lat, "lng": lng, "id_jenis": id_jenis, "tanggal": tgl, "sumber": sumber,
                          "akurasi": akurasi, "id_polsek": id_polsek, "berita": berita})
    if not errors and not hasil:
        errors.append("Berkas tidak berisi baris data")
    if errors:
        sisa = len(errors) - MAKS_ERROR_DITAMPILKAN
        raise validasi_gagal("CSV tidak valid", errors[:MAKS_ERROR_DITAMPILKAN] + ([f"...dan {sisa} error lain"] if sisa > 0 else []))
    return hasil
