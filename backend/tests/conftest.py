import os
import sys
from pathlib import Path

os.environ.setdefault("BCRYPT_ROUNDS", "4")        # hash cepat khusus tes (harus sebelum import app)

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # agar `import app` jalan dari folder backend/

from app.main import app  # noqa: E402
from tests.konstanta import PASSWORD_UJI, TAHUN_UJI  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:        # `with` -> lifespan (pool DB) ikut jalan
        yield c


@pytest.fixture(scope="session")
def db_hidup(client):
    """Lewati tes yang butuh database kalau DB belum menyala/terisi."""
    r = client.get("/api/health")
    if r.status_code != 200:
        pytest.skip("Database tidak terhubung (jalankan: docker compose up -d)")
    if len(client.get("/api/jenis").json()["data"]) == 0:
        pytest.skip("Database kosong (jalankan migrasi + impor, lihat README)")


@pytest.fixture()
def koneksi(db_hidup):
    """Koneksi langsung ke DB untuk tes SQL/zonasi. Semua perubahan di-rollback setelah tes."""
    import psycopg
    from psycopg.conninfo import make_conninfo
    from psycopg.rows import dict_row
    from app.config import settings

    c = psycopg.connect(make_conninfo(host=settings.db_host, port=settings.db_port, dbname=settings.db_name,
                                      user=settings.db_user, password=settings.db_password), row_factory=dict_row)
    try:
        yield c
    finally:
        c.rollback()
        c.close()


@pytest.fixture(scope="session")
def akun_uji(db_hidup):
    """Buat akun uji_admin & uji_operator (di-commit), dihapus setelah semua tes selesai."""
    import psycopg
    from app import security
    from app.db import conninfo

    with psycopg.connect(conninfo(), autocommit=True) as c:
        for nama, peran in (("uji_admin", "admin"), ("uji_operator", "operator")):
            c.execute("""INSERT INTO pengguna (username, password_hash, peran) VALUES (%s, %s, %s)
                         ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, peran = EXCLUDED.peran""",
                      (nama, security.hash_password(PASSWORD_UJI), peran))
    yield
    with psycopg.connect(conninfo(), autocommit=True) as c:
        c.execute("DELETE FROM pengguna WHERE username LIKE 'uji\\_%'")


@pytest.fixture(scope="session")
def header(client, akun_uji):
    """header['admin'] / header['operator'] -> {'Authorization': 'Bearer ...'}"""
    out = {}
    for peran in ("admin", "operator"):
        r = client.post("/api/auth/login", json={"username": f"uji_{peran}", "password": PASSWORD_UJI})
        assert r.status_code == 200, r.text
        out[peran] = {"Authorization": f"Bearer {r.json()['token']}"}
    return out


@pytest.fixture()
def bersih_tahun_uji(db_hidup):
    """Pastikan data tahun fiktif bersih sebelum & sesudah tes yang menulis (data asli 2024 tidak disentuh)."""
    import psycopg
    from app.db import conninfo

    def bersihkan():
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("DELETE FROM kasus_kejahatan WHERE tahun = ANY(%s)", (list(TAHUN_UJI),))
            c.execute("SELECT refresh_zona_kerawanan()")
    bersihkan()
    yield
    bersihkan()
