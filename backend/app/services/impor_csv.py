"""Impor rekap kriminalitas dari CSV (format sama dengan data/rekap_kriminalitas_2024.csv).

Kolom yang dipakai : Polsek (atau nama_polsek) + 18 kolom jenis (Aniaya ... Lain2). Kolom 'Jumlah' (opsional) dicek = jumlah 18 jenis.
Kolom lain (No, id_polsek, kategori_zona, ...) diabaikan. Pemisah , atau ; dan BOM Excel didukung.
"""
import csv
import io
import re

import psycopg

from app.errors import validasi_gagal

MAKS_BYTE = 2 * 1024 * 1024
MAKS_ERROR_DITAMPILKAN = 50

# kolom CSV -> kode_jenis di tabel jenis_kejahatan (urutan = id_jenis 1..18; cocok dengan data/scripts/bersihkan_csv.py)
KOLOM_JENIS = [
    ("Aniaya", "ANIAYA"), ("Aniaya Berat", "ANIAYA_BERAT"), ("Curas", "CURAS"), ("Curat", "CURAT"),
    ("Curanmor R4", "CURANMOR_R4"), ("Curanmor R2", "CURANMOR_R2"), ("Perkosaan", "PERKOSAAN"), ("Judi", "JUDI"),
    ("Rusak", "RUSAK"), ("Tipu", "TIPU"), ("Gelap", "GELAP"), ("Curi Biasa", "CURI_BIASA"), ("KDRT", "KDRT"),
    ("Sajam", "SAJAM"), ("Tdk Senang", "TDK_SENANG"), ("Keroyok", "KEROYOK"), ("Cabul", "CABUL"), ("Lain2", "LAIN2"),
]
KOREKSI_NAMA = {"Pemeugpeuk": "Pameungpeuk"}      # salah ketik di sumber data


def normalkan_nama(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^polsek\s+", "", s, flags=re.I).title()
    return KOREKSI_NAMA.get(s, s)


def _decode(isi: bytes) -> str:
    try:
        return isi.decode("utf-8-sig")
    except UnicodeDecodeError:
        return isi.decode("cp1252", errors="replace")


def baca_csv(isi: bytes, polsek_db: dict[str, int]) -> tuple[list[dict], list[str]]:
    """Parse + validasi. Mengembalikan (baris, peringatan). Melempar validasi_gagal(detail=[...]) bila ada error.
    polsek_db: {nama_polsek huruf kecil: id_polsek}. Tiap baris: {"id_polsek", "nama", "jumlah": {kode_jenis: int}}."""
    if len(isi) > MAKS_BYTE:
        raise validasi_gagal(f"Berkas terlalu besar (maksimal {MAKS_BYTE // 1024 // 1024} MB)", ["file"])
    teks = _decode(isi)
    baris_teks = teks.splitlines()
    if not baris_teks or not baris_teks[0].strip():
        raise validasi_gagal("Berkas kosong", ["file"])
    pemisah = ";" if baris_teks[0].count(";") > baris_teks[0].count(",") else ","
    rows = list(csv.reader(io.StringIO(teks), delimiter=pemisah))
    header = [h.strip() for h in rows[0]]
    idx = {h.lower(): i for i, h in enumerate(header)}

    kol_nama = idx.get("polsek", idx.get("nama_polsek"))
    hilang = [k for k, _ in KOLOM_JENIS if k.lower() not in idx]
    if kol_nama is None or hilang:
        detail = ([] if kol_nama is not None else ["Kolom 'Polsek' (atau 'nama_polsek') tidak ditemukan"]) + \
                 ([f"Kolom jenis tidak ditemukan: {', '.join(hilang)}"] if hilang else [])
        raise validasi_gagal("Format kolom CSV tidak sesuai", detail)
    kol_jumlah = idx.get("jumlah")

    errors: list[str] = []
    hasil: list[dict] = []
    terlihat: set[int] = set()
    for no, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r):
            continue                                            # baris kosong
        nama_asli = r[kol_nama].strip() if kol_nama < len(r) else ""
        nama = normalkan_nama(nama_asli)
        id_polsek = polsek_db.get(nama.lower())
        if id_polsek is None:
            errors.append(f"baris {no}: Polsek '{nama_asli}' tidak dikenal")
            continue
        if id_polsek in terlihat:
            errors.append(f"baris {no}: Polsek '{nama}' muncul lebih dari sekali")
            continue
        terlihat.add(id_polsek)
        jumlah, ok = {}, True
        for kolom, kode in KOLOM_JENIS:
            i = idx[kolom.lower()]
            sel = r[i].strip() if i < len(r) else ""
            if not re.fullmatch(r"\d+", sel):
                errors.append(f"baris {no} ({nama}): kolom '{kolom}' harus bilangan bulat >= 0 (isi: '{sel}')")
                ok = False
            else:
                jumlah[kode] = int(sel)
        if ok and kol_jumlah is not None and kol_jumlah < len(r) and r[kol_jumlah].strip() != "":
            tertulis = r[kol_jumlah].strip()
            if not re.fullmatch(r"\d+", tertulis) or int(tertulis) != sum(jumlah.values()):
                errors.append(f"baris {no} ({nama}): kolom 'Jumlah' ({tertulis}) tidak sama dengan jumlah 18 jenis ({sum(jumlah.values())})")
                ok = False
        if ok:
            hasil.append({"id_polsek": id_polsek, "nama": nama, "jumlah": jumlah})

    if not errors and not hasil:
        errors.append("Berkas tidak berisi baris data")
    if errors:
        sisa = len(errors) - MAKS_ERROR_DITAMPILKAN
        tampil = errors[:MAKS_ERROR_DITAMPILKAN] + ([f"...dan {sisa} error lain"] if sisa > 0 else [])
        raise validasi_gagal("CSV tidak valid", tampil)

    peringatan = []
    belum = sorted(n for n, i in polsek_db.items() if i not in terlihat)
    if belum:
        peringatan.append(f"{len(belum)} Polsek tidak ada di berkas: {', '.join(n.title() for n in belum)}")
    return hasil, peringatan


def simpan(conn: psycopg.Connection, tahun: int, baris: list[dict], mode: str) -> None:
    """mode 'timpa': hapus semua data tahun itu dulu. mode 'tambah': gabung (tambah yang baru, perbarui yang sudah ada)."""
    kode_ke_id = {r["kode_jenis"]: r["id_jenis"] for r in conn.execute("SELECT id_jenis, kode_jenis FROM jenis_kejahatan").fetchall()}
    if mode == "timpa":
        conn.execute("DELETE FROM kasus_kejahatan WHERE tahun = %s", (tahun,))
    data = [(b["id_polsek"], kode_ke_id[k], tahun, j) for b in baris for k, j in b["jumlah"].items()]
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO kasus_kejahatan (id_polsek, id_jenis, tahun, jumlah) VALUES (%s, %s, %s, %s)
               ON CONFLICT (id_polsek, id_jenis, tahun) DO UPDATE SET jumlah = EXCLUDED.jumlah""", data)
