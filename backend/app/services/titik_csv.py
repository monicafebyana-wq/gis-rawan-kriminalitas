"""Baca + validasi CSV titik kejadian.
Kolom (nama tidak peka huruf besar/kecil):  lat | latitude | lintang,  lng | lon | longitude | bujur,
jenis | kode_jenis | id_jenis (isi: kode seperti CURAT, nama jenis, atau id),  tanggal (YYYY-MM-DD atau DD/MM/YYYY).
Pemisah , atau ; (bila ; maka koma dibaca sebagai desimal). BOM Excel didukung. Maks 5 MB / 20.000 baris."""
import csv
import io
import math
from datetime import date, datetime

from app.errors import validasi_gagal
from app.services.geojson_polsek import BATAS_WILAYAH

MAKS_BYTE = 5 * 1024 * 1024
MAKS_BARIS = 20_000
MAKS_ERROR_DITAMPILKAN = 50
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
_ALIAS = {"lat": ("lat", "latitude", "lintang"), "lng": ("lng", "lon", "long", "longitude", "bujur"),
          "jenis": ("jenis", "kode_jenis", "id_jenis"), "tanggal": ("tanggal", "tgl", "date")}


def _tanggal(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def baca_csv(isi: bytes, jenis_db: dict[str, int]) -> list[dict]:
    """jenis_db: {KODE huruf besar | nama huruf kecil | id sebagai teks: id_jenis}. Melempar validasi_gagal(detail=[...])."""
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
    if len(rows) - 1 > MAKS_BARIS:
        raise validasi_gagal(f"Terlalu banyak baris (maksimal {MAKS_BARIS})", ["file"])

    x0, y0, x1, y1 = BATAS_WILAYAH
    errors: list[str] = []
    hasil: list[dict] = []
    for no, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue
        sel = {k: (r[i].strip() if i < len(r) else "") for k, i in kol.items()}
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
        tgl = _tanggal(sel["tanggal"])
        if tgl is None or not (TGL_MIN <= tgl <= TGL_MAX):
            masalah.append(f"tanggal '{sel['tanggal']}' tidak valid (pakai YYYY-MM-DD)")
        if masalah:
            errors.append(f"baris {no}: " + "; ".join(masalah))
        else:
            hasil.append({"lat": lat, "lng": lng, "id_jenis": id_jenis, "tanggal": tgl})
    if not errors and not hasil:
        errors.append("Berkas tidak berisi baris data")
    if errors:
        sisa = len(errors) - MAKS_ERROR_DITAMPILKAN
        raise validasi_gagal("CSV tidak valid", errors[:MAKS_ERROR_DITAMPILKAN] + ([f"...dan {sisa} error lain"] if sisa > 0 else []))
    return hasil
