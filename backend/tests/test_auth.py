"""Login, token, dan hash password."""
import time

import jwt
import pytest

from app import security
from app.config import settings
from tests.konstanta import PASSWORD_UJI


def login(client, user="uji_admin", password=PASSWORD_UJI):
    return client.post("/api/auth/login", json={"username": user, "password": password})


def test_login_berhasil(client, akun_uji):
    r = login(client)
    assert r.status_code == 200
    j = r.json()
    assert j["tipe"] == "Bearer" and j["berlaku_detik"] == settings.jwt_berlaku_detik and j["token"]
    assert j["pengguna"]["username"] == "uji_admin" and j["pengguna"]["peran"] == "admin"
    assert "password" not in str(j).lower() and "hash" not in str(j).lower()      # tidak bocor


@pytest.mark.parametrize("user, pw", [("uji_admin", "salah-total"), ("tidak_ada_user", PASSWORD_UJI), ("uji_admin", "x" * 150)])
def test_login_gagal_pesan_sama(client, akun_uji, user, pw):
    r = login(client, user, pw)
    assert r.status_code == 401
    assert r.json()["error"] == {"kode": "TIDAK_TERAUTENTIKASI", "pesan": "Username atau password salah", "detail": []}


def test_login_validasi_body(client, akun_uji):
    assert client.post("/api/auth/login", json={"username": "a"}).status_code == 400
    assert login(client, "uji_admin", "x" * 300).status_code == 400            # > 200 karakter ditolak lebih dulu


def test_me(client, header):
    r = client.get("/api/auth/me", headers=header["operator"])
    assert r.status_code == 200 and (r.json()["username"], r.json()["peran"]) == ("uji_operator", "operator")


@pytest.mark.parametrize("hdr", [None, {"Authorization": "Bearer bukan.token.valid"}, {"Authorization": "Basic abc"}])
def test_me_tanpa_token_valid(client, akun_uji, hdr):
    r = client.get("/api/auth/me", headers=hdr)
    assert r.status_code == 401 and r.json()["error"]["kode"] == "TIDAK_TERAUTENTIKASI"


def test_token_kedaluwarsa_atau_dipalsukan(client, akun_uji):
    sekarang = int(time.time())
    kedaluwarsa = jwt.encode({"sub": "1", "iat": sekarang - 100, "exp": sekarang - 50}, settings.jwt_secret, algorithm="HS256")
    palsu = jwt.encode({"sub": "1", "exp": sekarang + 100}, "secret-lain-yang-salah-0123456789", algorithm="HS256")
    for t in (kedaluwarsa, palsu):
        assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"}).status_code == 401


def test_token_user_sudah_dihapus(client, akun_uji):
    token = security.buat_token(999999, "admin")               # id yang tidak ada di DB
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_hash_bcrypt():
    h = security.hash_password("kata-sandi-aman")
    assert h.startswith("$2") and "kata-sandi-aman" not in h
    assert security.cocok("kata-sandi-aman", h) and not security.cocok("salah", h)
    assert security.hash_password("kata-sandi-aman") != h                       # salt acak
    assert not security.cocok("x" * 73, h)                                       # >72 byte selalu ditolak
    assert not security.cocok("apa-saja", "bukan-hash-bcrypt")
    with pytest.raises(ValueError):
        security.hash_password("x" * 73)
