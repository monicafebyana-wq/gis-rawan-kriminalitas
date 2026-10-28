"""Pembatas login gagal (429) + Retry-After."""
import pytest

from app import ratelimit
from app.config import settings
from tests.konstanta import PASSWORD_UJI


def login(client, user="uji_admin", pw=PASSWORD_UJI):
    return client.post("/api/auth/login", json={"username": user, "password": pw})


def test_blokir_setelah_gagal_beruntun(client, akun_uji):
    for _ in range(settings.login_maks_gagal):
        assert login(client, pw="salah-terus").status_code == 401
    r = login(client)                                              # password BENAR pun ditolak selama diblokir
    assert r.status_code == 429 and r.json()["error"]["kode"] == "TERLALU_BANYAK_PERCOBAAN"
    assert int(r.headers["Retry-After"]) > 0
    assert login(client, "uji_operator").status_code == 200        # username lain (dari IP sama) tidak ikut terblokir
    ratelimit.reset_semua()
    assert login(client).status_code == 200


def test_login_berhasil_mereset_hitungan(client, akun_uji):
    for _ in range(settings.login_maks_gagal - 1):
        login(client, pw="salah")
    assert login(client).status_code == 200                        # berhasil -> hitungan nol lagi
    for _ in range(settings.login_maks_gagal - 1):
        assert login(client, pw="salah").status_code == 401


def test_batas_per_ip_untuk_banyak_username(client, akun_uji, monkeypatch):
    monkeypatch.setattr(settings, "login_maks_gagal_ip", 3)
    for i in range(3):
        assert login(client, f"tidak_ada_{i}", "x").status_code == 401
    assert login(client, "tidak_ada_baru", "x").status_code == 429
    assert login(client).status_code == 429                        # akun sah dari IP yang sama ikut tertahan


def test_username_tidak_ada_dihitung_sama(client, akun_uji):
    for _ in range(settings.login_maks_gagal):
        login(client, "hantu", "x")
    assert login(client, "hantu", "x").status_code == 429          # perilaku sama dengan username yang ada -> tidak membocorkan
