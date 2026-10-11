"""Data referensi untuk dropdown filter: GET /api/jenis, GET /api/tahun  (sudah berfungsi penuh)."""
from fastapi import APIRouter

from app.db import Conn

router = APIRouter(tags=["Referensi"])


@router.get("/jenis", summary="Daftar jenis kejahatan")
def daftar_jenis(conn: Conn):
    rows = conn.execute("SELECT id_jenis, kode_jenis, nama_jenis FROM jenis_kejahatan ORDER BY id_jenis").fetchall()
    return {"data": rows}


@router.get("/tahun", summary="Tahun yang tersedia datanya")
def daftar_tahun(conn: Conn):
    tahun = [r["tahun"] for r in conn.execute("SELECT DISTINCT tahun FROM kasus_kejahatan ORDER BY tahun").fetchall()]
    return {"data": tahun, "terbaru": tahun[-1] if tahun else None}
