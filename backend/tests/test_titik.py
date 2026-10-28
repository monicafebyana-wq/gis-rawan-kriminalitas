"""Titik kejadian + heatmap. Titik uji bertanggal tahun 2099 (dibersihkan otomatis); poligon uji di luar Kab. Bandung."""
import psycopg
import pytest

from app.db import conninfo
from tests.test_geojson_spasial import KOTAK_A, geojson, polsek_uji, unggah  # noqa: F401  (polsek_uji = fixture)

DALAM = {"lat": -6.70, "lng": 108.05, "id_jenis": 1, "tanggal": "2099-03-01"}       # di dalam KOTAK_A
LUAR = {"lat": -6.62, "lng": 108.18, "id_jenis": 1, "tanggal": "2099-03-02"}         # dalam kotak validasi, di luar poligon uji


@pytest.fixture()
def bersih_titik(db_hidup):
    def bersihkan():
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("DELETE FROM titik_kejadian WHERE tanggal >= DATE '2099-01-01'")
    bersihkan()
    yield
    bersihkan()


def kirim_csv(client, header, isi: str, dry_run=False, peran="operator"):
    return client.post("/api/titik/import", headers=header[peran], data={"dry_run": str(dry_run).lower()},
                       files={"file": ("titik.csv", isi.encode(), "text/csv")})


def test_izin(client, header, bersih_titik):
    assert client.post("/api/titik", json=DALAM).status_code == 401
    assert client.get("/api/titik").status_code == 401                              # koordinat persis tidak publik
    assert client.get("/api/heatmap").status_code == 200                             # heatmap rangkuman: publik
    t = client.post("/api/titik", json=DALAM, headers=header["operator"])
    assert t.status_code == 201
    assert client.delete(f"/api/titik/{t.json()['id_titik']}", headers=header["operator"]).status_code == 403
    assert client.delete(f"/api/titik/{t.json()['id_titik']}", headers=header["admin"]).status_code == 204
    assert client.delete(f"/api/titik/{t.json()['id_titik']}", headers=header["admin"]).status_code == 404


def test_polsek_otomatis_dari_poligon(client, header, polsek_uji, bersih_titik):
    unggah(client, header, geojson(({"id_polsek": polsek_uji}, KOTAK_A)))
    dalam = client.post("/api/titik", json=DALAM, headers=header["operator"]).json()
    assert dalam["id_polsek"] == polsek_uji and dalam["nama_polsek"] == "Uji Spasial"
    assert (dalam["lat"], dalam["lng"], dalam["tanggal"]) == (-6.70, 108.05, "2099-03-01")
    luar = client.post("/api/titik", json=LUAR, headers=header["operator"]).json()
    assert luar["id_polsek"] is None and luar["nama_polsek"] is None

    # pindahkan titik luar ke dalam poligon -> polsek terisi; semua field boleh diubah
    r = client.put(f"/api/titik/{luar['id_titik']}", json={"lat": -6.71, "lng": 108.04, "id_jenis": 2, "tanggal": "2099-05-05"}, headers=header["operator"])
    assert r.status_code == 200
    j = r.json()
    assert (j["id_polsek"], j["id_jenis"], j["tanggal"], j["lat"], j["lng"]) == (polsek_uji, 2, "2099-05-05", -6.71, 108.04)
    r = client.put(f"/api/titik/{luar['id_titik']}", json={"tanggal": "2099-06-06"}, headers=header["operator"])          # ubah sebagian
    assert r.json()["lat"] == -6.71 and r.json()["tanggal"] == "2099-06-06" and r.json()["id_polsek"] == polsek_uji

    d = client.get("/api/titik?tahun=2099&limit=1&page=1", headers=header["operator"]).json()
    assert d["total_data"] == 2 and len(d["data"]) == 1
    assert client.get(f"/api/titik?tahun=2099&polsek={polsek_uji}&jenis=2", headers=header["operator"]).json()["total_data"] == 1
    assert client.get("/api/titik?tahun=2098", headers=header["operator"]).json()["total_data"] == 0


@pytest.mark.parametrize("ubah, field", [
    ({"lat": 95}, "lat"), ({"lng": 200}, "lng"), ({"lat": -6.7, "lng": 100.0}, "lng"),            # di luar kotak wilayah
    ({"lat": 108.05, "lng": -6.7}, "lat"),                                                          # tertukar
    ({"id_jenis": 99}, "id_jenis"), ({"id_polsek": 99999}, "id_polsek"),
    ({"tanggal": "1999-12-31"}, "tanggal"), ({"tanggal": "besok"}, "tanggal")])
def test_validasi_titik(client, header, bersih_titik, ubah, field):
    r = client.post("/api/titik", json={**DALAM, **ubah}, headers=header["operator"])
    assert r.status_code == 400 and field in r.json()["error"]["detail"]


def test_ubah_validasi(client, header, bersih_titik):
    t = client.post("/api/titik", json=DALAM, headers=header["operator"]).json()
    url = f"/api/titik/{t['id_titik']}"
    assert client.put(url, json={}, headers=header["operator"]).status_code == 400
    assert client.put(url, json={"lat": -6.7}, headers=header["operator"]).status_code == 400        # lat tanpa lng
    assert client.put(url, json={"tanggal": None}, headers=header["operator"]).status_code == 400
    assert client.put("/api/titik/9999999", json={"id_jenis": 1}, headers=header["operator"]).status_code == 404


def test_heatmap_agregasi(client, header, bersih_titik):
    for lat, lng in ((-6.7001, 108.0501), (-6.7002, 108.0502), (-6.6999, 108.0499)):               # satu kerumunan
        client.post("/api/titik", json={**DALAM, "lat": lat, "lng": lng}, headers=header["operator"])
    client.post("/api/titik", json={**LUAR, "tanggal": "2099-03-02"}, headers=header["operator"])
    h = client.get("/api/heatmap?tahun=2099&grid=0.01").json()
    assert (h["total_titik"], h["maks_bobot"], h["grid_derajat"]) == (4, 3, 0.01)
    assert h["data"][0]["bobot"] == 3 and abs(h["data"][0]["lat"] - -6.70) < 1e-9 and abs(h["data"][0]["lng"] - 108.05) < 1e-9
    assert [d["bobot"] for d in h["data"]] == [3, 1]
    assert client.get("/api/heatmap?tahun=2099&grid=0.0005").json()["total_titik"] == 4
    assert client.get("/api/heatmap?tahun=2098").json() == {"grid_derajat": 0.002, "total_titik": 0, "maks_bobot": 0, "data": []}
    assert client.get("/api/heatmap?tahun=2099&dari=2099-03-02&sampai=2099-03-02&grid=0.01").json()["total_titik"] == 1
    assert client.get("/api/heatmap?tahun=2099&jenis=2").json()["total_titik"] == 0
    assert "id_titik" not in client.get("/api/heatmap?tahun=2099").text                              # tidak membuka data baris
    for url in ("/api/heatmap?grid=0.00001", "/api/heatmap?grid=5", "/api/heatmap?jenis=a", "/api/heatmap?dari=x"):
        assert client.get(url).status_code == 400


CSV_BAIK = "lat;lng;jenis;tanggal\n-6,70;108,05;CURAT;2099-01-10\n-6,71;108,06;curanmor_r2;11/01/2099\n-6,62;108,18;1;2099-01-12\n"


def test_impor_csv(client, header, polsek_uji, bersih_titik):
    unggah(client, header, geojson(({"id_polsek": polsek_uji}, KOTAK_A)))
    r = kirim_csv(client, header, CSV_BAIK, dry_run=True)
    assert r.status_code == 200 and r.json()["tersimpan"] == 0 and r.json()["disimpan"] is False and r.json()["baris_dibaca"] == 3
    assert client.get("/api/heatmap?tahun=2099").json()["total_titik"] == 0                          # dry_run tidak menyimpan
    r = kirim_csv(client, header, CSV_BAIK)
    assert r.status_code == 200 and (r.json()["tersimpan"], r.json()["tanpa_polsek"]) == (3, 1) and r.json()["peringatan"]
    assert client.get("/api/heatmap?tahun=2099").json()["total_titik"] == 3
    isi = client.get(f"/api/titik?tahun=2099&polsek={polsek_uji}", headers=header["operator"]).json()
    assert isi["total_data"] == 2 and {d["id_jenis"] for d in isi["data"]} == {4, 6}                 # CURAT=4, nama/kode huruf kecil -> CURANMOR_R2=6
    # koma sebagai pemisah
    assert kirim_csv(client, header, "Latitude,Longitude,Kode_Jenis,Tgl\n-6.70,108.05,TIPU,2099-02-02\n").json()["tersimpan"] == 1


@pytest.mark.parametrize("isi, potongan", [
    ("lat,lng,jenis\n-6.7,108.05,CURAT\n", "tanggal"),                                           # kolom hilang
    ("lat,lng,jenis,tanggal\nabc,108.05,CURAT,2099-01-01\n", "bukan angka"),
    ("lat,lng,jenis,tanggal\n108.05,-6.7,CURAT,2099-01-01\n", "tertukar"),
    ("lat,lng,jenis,tanggal\n-6.7,108.05,NARKOBA,2099-01-01\n", "tidak dikenal"),
    ("lat,lng,jenis,tanggal\n-6.7,108.05,CURAT,31/02/2099\n", "tanggal"),
    ("lat,lng,jenis,tanggal\n", "tidak berisi baris data"),
    ("", "kosong")])
def test_impor_csv_tidak_valid(client, header, bersih_titik, isi, potongan):
    r = kirim_csv(client, header, isi)
    assert r.status_code == 400 and potongan in " ".join(r.json()["error"]["detail"] + [r.json()["error"]["pesan"]])


def test_impor_semua_atau_tidak_sama_sekali(client, header, bersih_titik):
    isi = "lat,lng,jenis,tanggal\n-6.7,108.05,CURAT,2099-01-01\n-6.7,108.05,SALAH,2099-01-01\n"
    r = kirim_csv(client, header, isi)
    assert r.status_code == 400 and "baris 3" in r.json()["error"]["detail"][0]
    assert client.get("/api/heatmap?tahun=2099").json()["total_titik"] == 0
    assert client.post("/api/titik/import", headers=header["operator"], files={"file": ("a.txt", b"x")}).status_code == 400
    assert client.post("/api/titik/import", files={"file": ("a.csv", b"x")}).status_code == 401


def test_titik_tercatat_di_audit(client, header, bersih_titik):
    t = client.post("/api/titik", json=DALAM, headers=header["operator"]).json()
    log = client.get("/api/audit?entitas=titik&username=uji_operator", headers=header["admin"]).json()["data"]
    assert any(x["id_entitas"] == str(t["id_titik"]) and x["aksi"] == "tambah" for x in log)


def test_hapus_polsek_titik_tetap_ada(client, header, polsek_uji, bersih_titik):
    unggah(client, header, geojson(({"id_polsek": polsek_uji}, KOTAK_A)))
    client.post("/api/titik", json=DALAM, headers=header["operator"])
    assert client.delete(f"/api/polsek/{polsek_uji}", headers=header["admin"]).status_code == 204     # titik TIDAK menghalangi hapus polsek
    d = client.get("/api/titik?tahun=2099", headers=header["operator"]).json()["data"]
    assert len(d) == 1 and d[0]["id_polsek"] is None
