"""Tes endpoint data: /polsek, /polsek/{id}, /kasus, /statistik, /statistik/tren.
Butuh DB menyala + sudah diimpor (migrasi, import.sh; poligon lewat import_poligon.sh untuk tes geometri)."""
import json
from pathlib import Path

import pytest

from app.services import zonasi

MOCK = Path(__file__).resolve().parents[2] / "data" / "mock"


def mock(nama):
    return json.loads((MOCK / nama).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- GET /api/polsek
def test_polsek_featurecollection(client, db_hidup):
    j = client.get("/api/polsek").json()
    assert j["type"] == "FeatureCollection" and len(j["features"]) == 27
    p = [f["properties"] for f in j["features"]]
    assert sum(x["total_kasus"] for x in p) == 1163
    assert {k: sum(1 for x in p if x["kategori_zona"] == k) for k in ("tinggi", "sedang", "rendah")} == {"tinggi": 10, "sedang": 7, "rendah": 10}
    cica = next(x for x in p if x["nama_polsek"] == "Cicalengka")
    assert (cica["total_kasus"], cica["kategori_zona"], cica["tahun"]) == (76, "tinggi", 2024)


def test_polsek_geometri_dan_pusat(client, db_hidup):
    fs = client.get("/api/polsek").json()["features"]
    if all(f["geometry"] is None for f in fs):
        pytest.skip("Poligon belum diimpor (jalankan: sh /seed/import_poligon.sh)")
    for f in fs:
        assert f["geometry"]["type"] == "MultiPolygon"
        pu = f["properties"]["pusat"]
        assert 107.2 < pu["lng"] < 108.2 and -7.6 < pu["lat"] < -6.6


def test_polsek_filter_jenis_zona_tetap_dari_total(client, db_hidup):
    j = client.get("/api/polsek?jenis=1,16&polsek=1").json()
    p = j["features"][0]["properties"]
    assert (p["total_kasus"], p["total_semua_jenis"], p["kategori_zona"]) == (21, 74, "tinggi")   # 4 + 17; zona dari 74


def test_polsek_filter_zona_dan_polsek(client, db_hidup):
    n = lambda q: len(client.get(f"/api/polsek?{q}").json()["features"])
    assert n("zona=tinggi") == 10 and n("zona=tinggi,sedang") == 17 and n("polsek=1,5") == 2 and n("zona=rendah&polsek=5") == 0


def test_polsek_zona_konsisten_dengan_aturan(client, koneksi):
    """API tidak boleh memberi zona yang beda dari aturan (menangkap tabel zona yang basi)."""
    for f in client.get("/api/polsek").json()["features"]:
        p = f["properties"]
        assert p["kategori_zona"] == zonasi.kategori_zona(koneksi, p["total_semua_jenis"])


@pytest.mark.parametrize("query, status", [("tahun=abc", 400), ("tahun=2031", 404), ("jenis=1,x", 400), ("zona=bahaya", 400), ("polsek=a", 400)])
def test_polsek_error(client, db_hidup, query, status):
    r = client.get(f"/api/polsek?{query}")
    assert r.status_code == status and "kode" in r.json()["error"]


# ---------------------------------------------------------------- GET /api/polsek/{id}
def test_detail_polsek(client, db_hidup):
    j = client.get("/api/polsek/1").json()
    assert (j["nama_polsek"], j["total_kasus"], j["kategori_zona"]) == ("Bale Endah", 74, "tinggi")
    r = j["rincian_jenis"]
    assert sum(x["jumlah"] for x in r) == 74 and all(x["jumlah"] > 0 for x in r)
    assert [x["jumlah"] for x in r] == sorted((x["jumlah"] for x in r), reverse=True)


def test_detail_polsek_tidak_ada(client, db_hidup):
    r = client.get("/api/polsek/99")
    assert r.status_code == 404 and r.json()["error"]["kode"] == "TIDAK_DITEMUKAN"


# ---------------------------------------------------------------- GET /api/kasus
def test_kasus_default(client, db_hidup):
    j = client.get("/api/kasus").json()
    assert (j["page"], j["limit"], j["total_data"], len(j["data"])) == (1, 20, 486, 20)
    ids = [x["id_kasus"] for x in j["data"]]
    assert ids == sorted(ids)
    assert set(j["data"][0]) == {"id_kasus", "id_polsek", "nama_polsek", "id_jenis", "nama_jenis", "tahun", "jumlah"}


def test_kasus_filter_dan_paginasi(client, db_hidup):
    g = lambda q: client.get(f"/api/kasus?{q}").json()
    assert g("polsek=1")["total_data"] == 18 and g("jenis=1")["total_data"] == 27
    satu = g("polsek=1&jenis=1")
    assert satu["total_data"] == 1 and satu["data"][0]["jumlah"] == 4
    h1, h2 = g("limit=100&page=1"), g("limit=100&page=2")
    assert len(h1["data"]) == 100 and h2["data"][0]["id_kasus"] > h1["data"][-1]["id_kasus"]
    assert g("page=999")["data"] == [] and g("tahun=2031") == {"page": 1, "limit": 20, "total_data": 0, "data": []}


@pytest.mark.parametrize("query", ["limit=101", "limit=0", "page=0", "jenis=1,x", "tahun=abc"])
def test_kasus_error_400(client, db_hidup, query):
    assert client.get(f"/api/kasus?{query}").status_code == 400


# ---------------------------------------------------------------- GET /api/statistik
def test_statistik(client, db_hidup):
    j = client.get("/api/statistik").json()
    assert (j["tahun"], j["total_kasus"], j["jumlah_polsek"], j["jumlah_jenis"]) == (2024, 1163, 27, 18)
    assert j["polsek_tertinggi"] == {"id_polsek": 5, "nama_polsek": "Cicalengka", "total_kasus": 76}
    assert j["polsek_terendah"]["nama_polsek"] == "Nagreg" and j["polsek_terendah"]["total_kasus"] == 5
    assert j["distribusi_zona"] == {"tinggi": 10, "sedang": 7, "rendah": 10}
    assert [(x["nama_jenis"], x["jumlah"]) for x in j["top_jenis"]] == [
        ("Penganiayaan", 235), ("Pengeroyokan", 198), ("Curanmor Roda 2", 154), ("Pencurian dengan Pemberatan (Curat)", 151)]
    assert j["persen_top_jenis"] == 63.5
    assert len(j["per_polsek"]) == 27 and len(j["per_jenis"]) == 18
    assert sum(x["jumlah"] for x in j["per_jenis"]) == 1163
    kasus = [x["total_kasus"] for x in j["per_polsek"]]
    assert kasus == sorted(kasus, reverse=True)


def test_statistik_top_dan_error(client, db_hidup):
    assert len(client.get("/api/statistik?top=2").json()["top_jenis"]) == 2
    assert client.get("/api/statistik?top=0").status_code == 400 and client.get("/api/statistik?top=19").status_code == 400
    assert client.get("/api/statistik?tahun=2031").status_code == 404


def test_tren(client, db_hidup):
    g = lambda q="": client.get(f"/api/statistik/tren?{q}").json()["data"]
    assert g() == [{"tahun": 2024, "total_kasus": 1163}]
    assert g("polsek=5")[0]["total_kasus"] == 76 and g("jenis=1")[0]["total_kasus"] == 235


# ---------------------------------------------------------------- kontrak = data mock Dhea
def test_kontrak_sama_dengan_mock(client, db_hidup):
    """Bentuk respons asli harus sama dengan data/mock (yang dipakai front end)."""
    a, m = client.get("/api/statistik").json(), mock("statistik.json")
    assert set(a) == set(m)
    for k in ("tahun", "total_kasus", "jumlah_polsek", "jumlah_jenis", "polsek_tertinggi", "polsek_terendah", "distribusi_zona", "top_jenis", "persen_top_jenis", "per_jenis"):
        assert a[k] == m[k], k
    assert {tuple(x.items()) for x in a["per_polsek"]} == {tuple(x.items()) for x in m["per_polsek"]}

    assert client.get("/api/polsek/1").json() == mock("polsek_detail_1.json")
    assert client.get("/api/jenis").json() == mock("jenis.json")
    assert client.get("/api/tahun").json() == mock("tahun.json")
    assert client.get("/api/statistik/tren").json()["data"] == mock("tren.json")["data"]

    k, mk = client.get("/api/kasus?limit=20").json(), mock("kasus.json")
    assert k == mk

    for nama, q in (("polsek.json", ""), ("polsek_filter_jenis_1_16.json", "?jenis=1,16")):
        api = {f["properties"]["id_polsek"]: f["properties"] for f in client.get(f"/api/polsek{q}").json()["features"]}
        for f in mock(nama)["features"]:
            mp = f["properties"]; ap = api[mp["id_polsek"]]
            assert set(ap) == set(mp)
            assert {k: v for k, v in ap.items() if k != "pusat"} == {k: v for k, v in mp.items() if k != "pusat"}
