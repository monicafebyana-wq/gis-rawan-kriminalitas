"""Impor CSV. Menulis ke tahun fiktif 2099 (dibersihkan otomatis)."""
from pathlib import Path

import pytest

CSV_ASLI = Path(__file__).resolve().parents[2] / "data" / "rekap_kriminalitas_2024.csv"
ISI = CSV_ASLI.read_bytes()


def impor(client, hdr, isi=ISI, nama="rekap.csv", **data):
    data = {"tahun": "2099", **data}
    return client.post("/api/import/csv", headers=hdr, data=data, files={"file": (nama, isi, "text/csv")})


def total_2099(client):
    r = client.get("/api/statistik?tahun=2099")
    return r.json()["total_kasus"] if r.status_code == 200 else None


def test_butuh_login(client, akun_uji):
    assert impor(client, None).status_code == 401


def test_dry_run_tidak_menyimpan(client, header, bersih_tahun_uji):
    r = impor(client, header["operator"], dry_run="true")
    assert r.status_code == 200
    assert r.json() == {"tahun": 2099, "baris_dibaca": 27, "baris_valid": 27, "total_kasus": 1163, "peringatan": [], "disimpan": False}
    assert total_2099(client) is None


def test_impor_penuh_total_1163(client, header, bersih_tahun_uji):
    r = impor(client, header["operator"])
    assert r.status_code == 200 and r.json()["disimpan"] is True and r.json()["total_kasus"] == 1163
    s = client.get("/api/statistik?tahun=2099").json()
    assert s["total_kasus"] == 1163 and s["jumlah_polsek"] == 27
    assert s["distribusi_zona"] == {"tinggi": 10, "sedang": 7, "rendah": 10}           # zona ikut terhitung
    assert s["polsek_tertinggi"]["nama_polsek"] == "Cicalengka" and s["polsek_tertinggi"]["total_kasus"] == 76
    assert client.get("/api/kasus?tahun=2099&limit=1").json()["total_data"] == 486


def test_impor_dua_kali_tidak_menggandakan(client, header, bersih_tahun_uji):
    impor(client, header["operator"]); impor(client, header["admin"])
    assert total_2099(client) == 1163


def test_format_titik_koma_dan_bom_excel(client, header, bersih_tahun_uji):
    teks = ISI.decode("utf-8").replace(",", ";")
    r = impor(client, header["operator"], ("\ufeff" + teks).encode("utf-8"), dry_run="true")
    assert r.status_code == 200 and r.json()["total_kasus"] == 1163


def test_mode_tambah_menggabung(client, header, bersih_tahun_uji):
    baris = ISI.decode("utf-8").splitlines()
    sebagian = "\n".join(baris[:3]).encode()                                   # header + 2 Polsek
    impor(client, header["operator"], sebagian, mode="timpa")
    r = impor(client, header["operator"], ("\n".join([baris[0], baris[3]])).encode(), mode="tambah")
    assert r.status_code == 200
    assert client.get("/api/statistik?tahun=2099").json()["total_kasus"] == 74 + 65 + 23     # 3 Polsek pertama (Bale Endah, Banjaran, Bojong Soang)


def test_nama_polsek_dinormalisasi(client, header, bersih_tahun_uji):
    teks = ISI.decode("utf-8").replace("POLSEK PEMEUGPEUK", "polsek  Pameungpeuk")
    assert impor(client, header["operator"], teks.encode(), dry_run="true").status_code == 200


def ubah_baris(no_baris, fn):
    baris = ISI.decode("utf-8").splitlines()
    baris[no_baris - 1] = fn(baris[no_baris - 1])
    return "\n".join(baris).encode()


@pytest.mark.parametrize("nama_kasus, isi, pesan", [
    ("jumlah tidak cocok", ubah_baris(2, lambda b: b.rsplit(",", 1)[0] + ",999"), "baris 2"),
    ("polsek tidak dikenal", ubah_baris(3, lambda b: b.replace("POLSEK BANJARAN", "POLSEK NGAWUR")), "NGAWUR"),
    ("angka negatif/bukan angka", ubah_baris(4, lambda b: b.replace(",2,", ",abc,", 1)), "baris 4"),
    ("polsek ganda", ISI + b"\n" + ISI.splitlines()[1], "lebih dari sekali"),
])
def test_csv_tidak_valid_400_dengan_nomor_baris(client, header, bersih_tahun_uji, nama_kasus, isi, pesan):
    r = impor(client, header["operator"], isi)
    assert r.status_code == 400, nama_kasus
    err = r.json()["error"]
    assert err["kode"] == "VALIDASI_GAGAL" and any(pesan in d for d in err["detail"]), err
    assert total_2099(client) is None                                          # tidak ada yang tersimpan


def test_kolom_hilang_dan_berkas_salah(client, header, bersih_tahun_uji):
    h = header["operator"]
    tanpa_kolom = ISI.decode().replace("Curat,", "X,", 1).encode()
    assert impor(client, h, tanpa_kolom).status_code == 400
    assert impor(client, h, b"", nama="kosong.csv").status_code == 400
    assert impor(client, h, ISI, nama="data.txt").status_code == 400
    assert impor(client, h, b"x" * (2 * 1024 * 1024 + 10)).status_code == 400
    assert impor(client, h, ISI, mode="hapus_semua").status_code == 400
    assert impor(client, h, ISI, tahun="1800").status_code == 400
