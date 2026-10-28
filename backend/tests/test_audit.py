"""Audit log: perubahan tercatat, hanya admin yang boleh membaca."""
from tests.test_kasus_crud import BARU


def test_audit_hanya_admin(client, header):
    assert client.get("/api/audit").status_code == 401
    assert client.get("/api/audit", headers=header["operator"]).status_code == 403


def test_perubahan_kasus_tercatat(client, header, bersih_tahun_uji):
    k = client.post("/api/kasus", json=BARU, headers=header["operator"]).json()
    client.put(f"/api/kasus/{k['id_kasus']}", json={"jumlah": 7}, headers=header["operator"])
    client.delete(f"/api/kasus/{k['id_kasus']}", headers=header["admin"])
    r = client.get(f"/api/audit?entitas=kasus&limit=50&username=uji_operator", headers=header["admin"])
    assert r.status_code == 200
    log = [x for x in r.json()["data"] if x["id_entitas"] == str(k["id_kasus"])]
    assert [x["aksi"] for x in log] == ["ubah", "tambah"]                         # terbaru dulu
    assert log[0]["detail"]["sebelum"]["jumlah"] == 61 and log[0]["detail"]["sesudah"]["jumlah"] == 7
    hapus = client.get("/api/audit?entitas=kasus&aksi=hapus&username=uji_admin", headers=header["admin"]).json()["data"]
    assert any(x["id_entitas"] == str(k["id_kasus"]) and x["detail"]["jumlah"] == 7 for x in hapus)


def test_audit_tidak_memuat_password(client, header):
    client.post("/api/pengguna", json={"username": "uji_audit1", "password": "rahasia-banget-1"}, headers=header["admin"])
    teks = client.get("/api/audit?entitas=pengguna&limit=100", headers=header["admin"]).text.lower()
    assert "uji_audit1" in teks and "rahasia-banget-1" not in teks and "password_hash" not in teks
    uid = [p["id_pengguna"] for p in client.get("/api/pengguna", headers=header["admin"]).json()["data"] if p["username"] == "uji_audit1"][0]
    client.delete(f"/api/pengguna/{uid}", headers=header["admin"])


def test_filter_dan_paginasi(client, header):
    assert client.get("/api/audit?limit=1&page=1", headers=header["admin"]).json()["limit"] == 1
    assert client.get("/api/audit?dari=2999-01-01", headers=header["admin"]).json()["total_data"] == 0
    assert client.get("/api/audit?dari=bukan-tanggal", headers=header["admin"]).status_code == 400
    assert client.get("/api/audit?limit=1000", headers=header["admin"]).status_code == 400


def test_gagal_tidak_tercatat(client, header, bersih_tahun_uji):
    sebelum = client.get("/api/audit?entitas=kasus", headers=header["admin"]).json()["total_data"]
    assert client.post("/api/kasus", json={**BARU, "id_polsek": 99999}, headers=header["operator"]).status_code == 400
    assert client.get("/api/audit?entitas=kasus", headers=header["admin"]).json()["total_data"] == sebelum
