from fastapi import APIRouter

from app import __version__
from app.db import Conn

router = APIRouter(tags=["Sistem"])


@router.get("/health", summary="Cek API, koneksi database, dan PostGIS")
def health(conn: Conn):
    postgis = conn.execute("SELECT PostGIS_Version() AS v").fetchone()["v"]
    return {"status": "ok", "versi_api": __version__, "database": "terhubung", "postgis": postgis}
