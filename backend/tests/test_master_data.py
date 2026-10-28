"""CRUD master Polsek & jenis kejahatan (khusus admin) + audit log."""
import psycopg
import pytest

from app.db import conninfo

NAMA = "Uji Master"
KODE = "UJI_JENIS"


@pytest.fixture()
def bersih_master(db_hidup):
    def bersihkan():
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("DELETE FROM kasus_kejahatan WHERE id_polsek IN (SELECT id_polsek FROM polsek WHERE nama_polsek LIKE 'Uji Master%')")
            c.execute("DELETE FROM polsek WHERE nama_polsek LIKE 'Uji Master%'")
            c.execute("DELETE FROM jenis_kejahatan WHERE kode_jenis LIKE 'UJI\\_%'")
    bersihkan()
    yield
    bersihkan()


@pytest.mark.parametrize("metode, url, body", [
    ("post", "/api/polsek", {"nama_polsek": NAMA}), ("put", "/api/polsek/1", {"nama_polsek": "Xyz Abc"}), ("delete", "/api/polsek/1", None),
    ("post", "/api/jenis", {"kode_jenis": KODE, "nama_jenis": "Uji"}), ("put", "/api/jenis/1", {"nama_jenis": "Uji"}), ("delete", "/api/jenis/1", None)])
def test_hanya_admin(client, header, metode, url, body):
    kw = {"json": body} if body else {}
    assert getattr(client, metode)(url, **kw).status_code == 401
    assert getattr(client, metode)(url, headers=header["operator"], **kw).status_code == 403


def test_crud_polsek(client, header, bersih_master):
    r = client.post("/api/polsek", json={"nama_polsek": "POLSEK  uji   master", "nama_wilayah_resmi": "Kec. Uji"}, headers=header["admin"])
    assert r.status_code == 201
    p = r.json()
    assert p["nama_polsek"] == NAMA and p["punya_poligon"] is False            # nama dinormalkan seperti impor CSV
    assert client.post("/api/polsek", json={"nama_polsek": "uji master"}, headers=header["admin"]).status_code == 409   # kembar (huruf besar/kecil)

    r = client.put(f"/api/polsek/{p['id_polsek']}", json={"nama_polsek": "Uji Master Dua"}, headers=header["admin"])
    assert r.status_code == 200 and r.json()["nama_polsek"] == "Uji Master Dua" and r.json()["nama_wilayah_resmi"] == "Kec. Uji"
    r = client.put(f"/api/polsek/{p['id_polsek']}", json={"nama_wilayah_resmi": None}, headers=header["admin"])      # null eksplisit = kosongkan
    assert r.status_code == 200 and r.json()["nama_wilayah_resmi"] is None
    assert client.put(f"/api/polsek/{p['id_polsek']}", json={}, headers=header["admin"]).status_code == 400
    assert client.put(f"/api/polsek/{p['id_polsek']}", json={"nama_polsek": None}, headers=header["admin"]).status_code == 400
    assert client.put("/api/polsek/9999999", json={"nama_polsek": "Xyz Abc"}, headers=header["admin"]).status_code == 404

    assert client.delete(f"/api/polsek/{p['id_polsek']}", headers=header["admin"]).status_code == 204
    assert client.delete(f"/api/polsek/{p['id_polsek']}", headers=header["admin"]).status_code == 404


def test_hapus_polsek_berkasus_ditolak(client, header, bersih_master, bersih_tahun_uji):
    p = client.post("/api/polsek", json={"nama_polsek": NAMA}, headers=header["admin"]).json()
    k = client.post("/api/kasus", json={"id_polsek": p["id_polsek"], "id_jenis": 1, "tahun": 2099, "jumlah": 3}, headers=header["operator"])
    assert k.status_code == 201
    r = client.delete(f"/api/polsek/{p['id_polsek']}", headers=header["admin"])
    assert r.status_code == 409 and r.json()["error"]["kode"] == "AKSI_DITOLAK"
    assert client.get(f"/api/polsek/{p['id_polsek']}?tahun=2099").status_code == 200       # masih ada


def test_polsek_baru_langsung_punya_zona(client, header, bersih_master, bersih_tahun_uji):
    client.post("/api/kasus", json={"id_polsek": 1, "id_jenis": 1, "tahun": 2099, "jumlah": 1}, headers=header["operator"])
    p = client.post("/api/polsek", json={"nama_polsek": NAMA}, headers=header["admin"]).json()
    d = client.get(f"/api/polsek/{p['id_polsek']}?tahun=2099").json()
    assert d["total_kasus"] == 0 and d["kategori_zona"] == "rendah"


def test_crud_jenis(client, header, bersih_master):
    r = client.post("/api/jenis", json={"kode_jenis": KODE, "nama_jenis": "Jenis Uji"}, headers=header["admin"])
    assert r.status_code == 201
    j = r.json()
    assert client.post("/api/jenis", json={"kode_jenis": KODE, "nama_jenis": "Lagi"}, headers=header["admin"]).status_code == 409
    assert client.post("/api/jenis", json={"kode_jenis": "kecil", "nama_jenis": "Salah"}, headers=header["admin"]).status_code == 400
    assert KODE in [x["kode_jenis"] for x in client.get("/api/jenis").json()["data"]]

    r = client.put(f"/api/jenis/{j['id_jenis']}", json={"kode_jenis": "UJI_BARU", "nama_jenis": "Nama Baru"}, headers=header["admin"])
    assert r.status_code == 200 and (r.json()["kode_jenis"], r.json()["nama_jenis"]) == ("UJI_BARU", "Nama Baru")
    assert client.put(f"/api/jenis/{j['id_jenis']}", json={}, headers=header["admin"]).status_code == 400
    assert client.put(f"/api/jenis/{j['id_jenis']}", json={"kode_jenis": "ANIAYA"}, headers=header["admin"]).status_code == 409   # kode bentrok
    assert client.delete(f"/api/jenis/{j['id_jenis']}", headers=header["admin"]).status_code == 204
    assert client.delete(f"/api/jenis/{j['id_jenis']}", headers=header["admin"]).status_code == 404


def test_jenis_baku_dilindungi(client, header):
    assert client.delete("/api/jenis/1", headers=header["admin"]).status_code == 409
    assert client.put("/api/jenis/1", json={"kode_jenis": "LAIN"}, headers=header["admin"]).status_code == 409


def test_hapus_jenis_berkasus_ditolak(client, header, bersih_master, bersih_tahun_uji):
    j = client.post("/api/jenis", json={"kode_jenis": KODE, "nama_jenis": "Jenis Uji"}, headers=header["admin"]).json()
    assert client.post("/api/kasus", json={"id_polsek": 1, "id_jenis": j["id_jenis"], "tahun": 2099, "jumlah": 2}, headers=header["operator"]).status_code == 201
    assert client.delete(f"/api/jenis/{j['id_jenis']}", headers=header["admin"]).status_code == 409
