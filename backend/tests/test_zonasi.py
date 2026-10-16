"""Tes klasifikasi zona + isi tabel zona_kerawanan (butuh DB menyala & sudah diimpor)."""
import csv
from pathlib import Path

import pytest

from app.services import zonasi

CSV_REKAP = Path(__file__).resolve().parents[2] / "data" / "bersih" / "rekap_2024_bersih.csv"


@pytest.mark.parametrize("total, harapan", [
    (0, "rendah"), (5, "rendah"), (29, "rendah"),      # < 30
    (30, "sedang"), (45, "sedang"), (59, "sedang"),    # 30-59
    (60, "tinggi"), (61, "tinggi"), (76, "tinggi"),    # >= 60
])
def test_batas_klasifikasi(koneksi, total, harapan):
    assert zonasi.kategori_zona(koneksi, total) == harapan


def test_tabel_zona_2024_terisi(koneksi):
    zona = zonasi.ambil_zona(koneksi, 2024)
    assert len(zona) == 27                                   # semua Polsek punya zona
    assert sum(z["total_kasus"] for z in zona) == 1163       # total sama dengan slide/CSV
    dist = {k: sum(1 for z in zona if z["kategori_zona"] == k) for k in ("tinggi", "sedang", "rendah")}
    assert dist == {"tinggi": 10, "sedang": 7, "rendah": 10}
    assert zona[0]["nama_polsek"] == "Cicalengka" and zona[0]["total_kasus"] == 76
    assert zona[-1]["nama_polsek"] == "Nagreg" and zona[-1]["total_kasus"] == 5


def test_zona_cocok_dengan_csv(koneksi):
    """Setiap Polsek: kategori di database == kategori di rekap CSV hasil pembersihan."""
    dari_db = {z["id_polsek"]: z["kategori_zona"] for z in zonasi.ambil_zona(koneksi, 2024)}
    with open(CSV_REKAP, encoding="utf-8") as f:
        dari_csv = {int(r["id_polsek"]): r["kategori_zona"] for r in csv.DictReader(f)}
    assert dari_db == dari_csv


def test_refresh_idempoten(koneksi):
    a = zonasi.ambil_zona(koneksi, 2024)
    assert zonasi.refresh_zona(koneksi, 2024) == 27
    assert zonasi.refresh_zona(koneksi) >= 27                # semua tahun
    assert zonasi.ambil_zona(koneksi, 2024) == a             # hasil tidak berubah


def test_zona_ikut_berubah_saat_data_berubah(koneksi):
    """Nagreg (5 kasus, rendah) +55 kasus -> 60 -> harus jadi 'tinggi' setelah refresh; lalu di-rollback."""
    nagreg = koneksi.execute("SELECT id_polsek FROM polsek WHERE nama_polsek = 'Nagreg'").fetchone()["id_polsek"]
    koneksi.execute("UPDATE kasus_kejahatan SET jumlah = jumlah + 55 WHERE id_polsek = %s AND id_jenis = 1 AND tahun = 2024", (nagreg,))
    zonasi.refresh_zona(koneksi, 2024)
    z = {x["id_polsek"]: x for x in zonasi.ambil_zona(koneksi, 2024)}[nagreg]
    assert z["total_kasus"] == 60 and z["kategori_zona"] == "tinggi"
    # kembali ke 59 -> 'sedang' (batas bawah-atas)
    koneksi.execute("UPDATE kasus_kejahatan SET jumlah = jumlah - 1 WHERE id_polsek = %s AND id_jenis = 1 AND tahun = 2024", (nagreg,))
    zonasi.refresh_zona(koneksi, 2024)
    z = {x["id_polsek"]: x for x in zonasi.ambil_zona(koneksi, 2024)}[nagreg]
    assert z["total_kasus"] == 59 and z["kategori_zona"] == "sedang"


def test_tahun_tanpa_data_tidak_membuat_zona(koneksi):
    assert zonasi.refresh_zona(koneksi, 2031) == 0
    assert zonasi.ambil_zona(koneksi, 2031) == []
