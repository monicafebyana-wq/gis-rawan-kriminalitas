"""CRUD kasus + hak akses peran. Menulis ke tahun fiktif 2099 (dibersihkan otomatis)."""
import pytest

BARU = {"id_polsek": 1, "id_jenis": 1, "tahun": 2099, "jumlah": 61}


def zona_2099(client, id_polsek=1):
    f = [x for x in client.get("/api/polsek?tahun=2099").json()["features"] if x["properties"]["id_polsek"] == id_polsek]
    return f[0]["properties"]


@pytest.mark.parametrize("metode, url, body", [("post", "/api/kasus", BARU), ("put", "/api/kasus/1", {"jumlah": 1}), ("delete", "/api/kasus/1", None)])
def test_tanpa_login_401(client, akun_uji, metode, url, body):
    r = getattr(client, metode)(url, **({"json": body} if body else {}))
    assert r.status_code == 401


def test_alur_crud_dan_zona_ikut_berubah(client, header, bersih_tahun_uji):
    # CREATE (operator boleh)
    r = client.post("/api/kasus", json=BARU, headers=header["operator"])
    assert r.status_code == 201
    k = r.json()
    assert {k_: k[k_] for k_ in ("id_polsek", "id_jenis", "tahun", "jumlah")} == BARU and k["id_kasus"] > 486
    assert (zona_2099(client)["total_kasus"], zona_2099(client)["kategori_zona"]) == (61, "tinggi")     # zona langsung ter-refresh

    # tampil di GET /api/kasus & /api/tahun
    assert client.get("/api/kasus?tahun=2099").json()["total_data"] == 1
    assert 2099 in client.get("/api/tahun").json()["data"]

    # duplikat -> 409
    r = client.post("/api/kasus", json=BARU, headers=header["operator"])
    assert r.status_code == 409 and r.json()["error"]["kode"] == "DATA_SUDAH_ADA"

    # UPDATE (operator boleh): 61 -> 10 = rendah
    r = client.put(f"/api/kasus/{k['id_kasus']}", json={"jumlah": 10}, headers=header["operator"])
    assert r.status_code == 200 and r.json()["jumlah"] == 10
    assert zona_2099(client)["kategori_zona"] == "rendah"
    r = client.put(f"/api/kasus/{k['id_kasus']}", json={"jumlah": 30}, headers=header["operator"])
    assert zona_2099(client)["kategori_zona"] == "sedang"                                               # batas 30

    # DELETE: operator 403, admin 204
    r = client.delete(f"/api/kasus/{k['id_kasus']}", headers=header["operator"])
    assert r.status_code == 403 and r.json()["error"]["kode"] == "TIDAK_DIIZINKAN"
    assert client.delete(f"/api/kasus/{k['id_kasus']}", headers=header["admin"]).status_code == 204
    assert client.get("/api/kasus?tahun=2099").json()["total_data"] == 0
    assert 2099 not in client.get("/api/tahun").json()["data"]                                           # tahun hilang lagi
    assert client.delete(f"/api/kasus/{k['id_kasus']}", headers=header["admin"]).status_code == 404     # sudah terhapus


def test_data_2024_tidak_terpengaruh(client, header, bersih_tahun_uji):
    client.post("/api/kasus", json=BARU, headers=header["admin"])
    s = client.get("/api/statistik?tahun=2024").json()
    assert s["total_kasus"] == 1163 and s["distribusi_zona"] == {"tinggi": 10, "sedang": 7, "rendah": 10}


@pytest.mark.parametrize("ubah, field", [
    ({"id_polsek": 99}, "id_polsek"), ({"id_jenis": 99}, "id_jenis"),
    ({"jumlah": -1}, "jumlah"), ({"tahun": 1999}, "tahun"), ({"jumlah": "banyak"}, "jumlah"),
])
def test_validasi_body(client, header, bersih_tahun_uji, ubah, field):
    r = client.post("/api/kasus", json={**BARU, **ubah}, headers=header["operator"])
    assert r.status_code == 400
    assert field in r.json()["error"]["detail"]


def test_ubah_hapus_id_tidak_ada_404(client, header):
    assert client.put("/api/kasus/9999999", json={"jumlah": 1}, headers=header["operator"]).status_code == 404
    assert client.delete("/api/kasus/9999999", headers=header["admin"]).status_code == 404
    assert client.put("/api/kasus/1", json={"jumlah": -5}, headers=header["operator"]).status_code == 400
