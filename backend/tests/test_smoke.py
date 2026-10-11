"""Tes dasar. Yang berlabel (DB) butuh database menyala + sudah diimpor."""


def test_health(client, db_hidup):
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok" and j["database"] == "terhubung" and j["postgis"]


def test_jenis_18(client, db_hidup):
    data = client.get("/api/jenis").json()["data"]
    assert len(data) == 18
    assert data[0] == {"id_jenis": 1, "kode_jenis": "ANIAYA", "nama_jenis": "Penganiayaan"}


def test_tahun(client, db_hidup):
    j = client.get("/api/tahun").json()
    assert j["terbaru"] == max(j["data"])


def test_endpoint_belum_dikerjakan_pakai_format_error(client, db_hidup):
    r = client.get("/api/statistik")
    assert r.status_code == 501
    assert r.json()["error"]["kode"] == "BELUM_DIIMPLEMENTASI"


def test_validasi_tahun_bukan_angka(client, db_hidup):
    r = client.get("/api/polsek?tahun=abc")
    assert r.status_code == 400
    assert r.json() == {"error": {"kode": "VALIDASI_GAGAL", "pesan": "Parameter atau body tidak valid", "detail": ["tahun"]}}


def test_validasi_daftar_jenis(client, db_hidup):
    r = client.get("/api/kasus?jenis=1,x")
    assert r.status_code == 400
    assert r.json()["error"]["detail"] == ["jenis"]


def test_endpoint_tidak_ada(client):
    r = client.get("/api/tidak-ada")
    assert r.status_code == 404
    assert r.json()["error"]["kode"] == "TIDAK_DITEMUKAN"
