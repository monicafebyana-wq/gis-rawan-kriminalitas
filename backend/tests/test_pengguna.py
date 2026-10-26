"""Manajemen akun (khusus admin) + ganti password sendiri. Akun uji berawalan 'uji_baru' dibersihkan otomatis."""
import psycopg
import pytest

from app.db import conninfo
from tests.konstanta import PASSWORD_UJI

BARU = {"username": "uji_baru_1", "password": "password-baru-123", "peran": "operator"}


@pytest.fixture()
def bersih_akun_baru(db_hidup):
    def bersihkan():
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("DELETE FROM pengguna WHERE username LIKE 'uji\\_baru%'")
    bersihkan()
    yield
    bersihkan()


def login(client, user, pw):
    return client.post("/api/auth/login", json={"username": user, "password": pw})


@pytest.mark.parametrize("metode, url, body", [
    ("get", "/api/pengguna", None), ("post", "/api/pengguna", BARU),
    ("put", "/api/pengguna/1", {"peran": "admin"}), ("delete", "/api/pengguna/1", None)])
def test_tanpa_login_401_operator_403(client, header, metode, url, body):
    kw = {"json": body} if body else {}
    assert getattr(client, metode)(url, **kw).status_code == 401
    r = getattr(client, metode)(url, headers=header["operator"], **kw)
    assert r.status_code == 403 and r.json()["error"]["kode"] == "TIDAK_DIIZINKAN"


def test_admin_daftarkan_akun_baru(client, header, bersih_akun_baru):
    r = client.post("/api/pengguna", json={**BARU, "peran": "admin"}, headers=header["admin"])
    assert r.status_code == 201
    j = r.json()
    assert j["username"] == "uji_baru_1" and j["peran"] == "admin" and "password" not in str(j).lower()
    assert login(client, "uji_baru_1", BARU["password"]).status_code == 200            # akun langsung bisa dipakai

    d = client.post("/api/pengguna", json=BARU, headers=header["admin"])               # username kembar
    assert d.status_code == 409 and d.json()["error"]["kode"] == "DATA_SUDAH_ADA"

    daftar = client.get("/api/pengguna", headers=header["admin"]).json()["data"]
    assert "uji_baru_1" in [p["username"] for p in daftar] and "hash" not in str(daftar).lower()


def test_peran_default_operator(client, header, bersih_akun_baru):
    r = client.post("/api/pengguna", json={"username": "uji_baru_2", "password": "password-baru-123"}, headers=header["admin"])
    assert r.status_code == 201 and r.json()["peran"] == "operator"


@pytest.mark.parametrize("ubah, field", [
    ({"username": "a"}, "username"), ({"username": "ada spasi"}, "username"),
    ({"password": "pendek"}, "password"), ({"password": "é" * 40}, "password"),        # 80 byte > 72
    ({"peran": "superuser"}, "peran")])
def test_validasi_akun_baru(client, header, bersih_akun_baru, ubah, field):
    r = client.post("/api/pengguna", json={**BARU, **ubah}, headers=header["admin"])
    assert r.status_code == 400 and field in r.json()["error"]["detail"]


def test_ubah_peran_dan_reset_password(client, header, bersih_akun_baru):
    id_ = client.post("/api/pengguna", json=BARU, headers=header["admin"]).json()["id_pengguna"]
    r = client.put(f"/api/pengguna/{id_}", json={"peran": "admin", "password": "password-reset-9"}, headers=header["admin"])
    assert r.status_code == 200 and r.json()["peran"] == "admin"
    assert login(client, "uji_baru_1", BARU["password"]).status_code == 401           # password lama mati
    assert login(client, "uji_baru_1", "password-reset-9").json()["pengguna"]["peran"] == "admin"

    assert client.put(f"/api/pengguna/{id_}", json={}, headers=header["admin"]).status_code == 400
    assert client.put("/api/pengguna/9999999", json={"peran": "admin"}, headers=header["admin"]).status_code == 404


def test_hapus_akun(client, header, bersih_akun_baru):
    id_ = client.post("/api/pengguna", json=BARU, headers=header["admin"]).json()["id_pengguna"]
    assert client.delete(f"/api/pengguna/{id_}", headers=header["admin"]).status_code == 204
    assert login(client, "uji_baru_1", BARU["password"]).status_code == 401
    assert client.delete(f"/api/pengguna/{id_}", headers=header["admin"]).status_code == 404


def test_tidak_bisa_hapus_akun_sendiri(client, header):
    saya = client.get("/api/auth/me", headers=header["admin"]).json()["id_pengguna"]
    r = client.delete(f"/api/pengguna/{saya}", headers=header["admin"])
    assert r.status_code == 409 and r.json()["error"]["kode"] == "AKSI_DITOLAK"


def test_admin_terakhir_tidak_bisa_diturunkan_atau_dihapus(client, db_hidup, bersih_akun_baru):
    """Buat admin tunggal sementara: semua admin lain diturunkan lalu DIPULIHKAN di akhir tes."""
    from app import security
    with psycopg.connect(conninfo(), autocommit=True) as c:
        lain = [r[0] for r in c.execute("SELECT id_pengguna FROM pengguna WHERE peran = 'admin' AND username NOT LIKE 'uji\\_baru%%'").fetchall()]
        c.execute("INSERT INTO pengguna (username, password_hash, peran) VALUES ('uji_baru_solo', %s, 'admin')",
                  (security.hash_password(PASSWORD_UJI),))
        c.execute("UPDATE pengguna SET peran = 'operator' WHERE id_pengguna = ANY(%s)", (lain,))
    try:
        tok = {"Authorization": f"Bearer {login(client, 'uji_baru_solo', PASSWORD_UJI).json()['token']}"}
        saya = client.get("/api/auth/me", headers=tok).json()["id_pengguna"]
        r = client.put(f"/api/pengguna/{saya}", json={"peran": "operator"}, headers=tok)
        assert r.status_code == 409 and r.json()["error"]["kode"] == "AKSI_DITOLAK"
        assert client.get("/api/auth/me", headers=tok).json()["peran"] == "admin"          # tetap admin (rollback)
    finally:
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("UPDATE pengguna SET peran = 'admin' WHERE id_pengguna = ANY(%s)", (lain,))


def test_ganti_password_sendiri(client, header, bersih_akun_baru):
    client.post("/api/pengguna", json=BARU, headers=header["admin"])
    tok = {"Authorization": f"Bearer {login(client, 'uji_baru_1', BARU['password']).json()['token']}"}
    salah = client.post("/api/auth/ubah-password", json={"password_lama": "salah", "password_baru": "password-baru-456"}, headers=tok)
    assert salah.status_code == 400 and "password_lama" in salah.json()["error"]["detail"]
    pendek = client.post("/api/auth/ubah-password", json={"password_lama": BARU["password"], "password_baru": "pendek"}, headers=tok)
    assert pendek.status_code == 400
    ok = client.post("/api/auth/ubah-password", json={"password_lama": BARU["password"], "password_baru": "password-baru-456"}, headers=tok)
    assert ok.status_code == 204
    assert login(client, "uji_baru_1", BARU["password"]).status_code == 401
    assert login(client, "uji_baru_1", "password-baru-456").status_code == 200
    assert client.post("/api/auth/ubah-password", json={"password_lama": "x", "password_baru": "password-baru-456"}).status_code == 401
