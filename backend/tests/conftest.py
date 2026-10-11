import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # agar `import app` jalan dari folder backend/

from app.main import app  # noqa: E402


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
