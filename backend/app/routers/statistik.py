"""Dashboard. TODO: tugas "Endpoint GET /api/statistik" (No 19) + tren. Lihat api-contract.md bagian 2.6 & 2.7."""
from fastapi import APIRouter, Query

from app.db import Conn
from app.errors import belum_diimplementasi
from app.params import daftar_int

router = APIRouter(tags=["Statistik"])


@router.get("/statistik", summary="Ringkasan dashboard")
def statistik(conn: Conn, tahun: int | None = None, top: int = Query(4, ge=1, le=18)):
    raise belum_diimplementasi("GET /api/statistik")


@router.get("/statistik/tren", summary="Tren per tahun")
def tren(conn: Conn, polsek: str | None = None, jenis: str | None = None):
    daftar_int(polsek, "polsek"), daftar_int(jenis, "jenis")
    raise belum_diimplementasi("GET /api/statistik/tren")
