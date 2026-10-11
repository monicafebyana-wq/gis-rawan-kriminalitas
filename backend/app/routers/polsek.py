"""Peta utama & popup. TODO: tugas "Endpoint GET /api/polsek" (No 17).
Filter & format respons: lihat docs/api-contract.md bagian 2.1 dan 2.2."""
from fastapi import APIRouter, Query

from app.db import Conn
from app.errors import belum_diimplementasi
from app.params import daftar_int, daftar_zona

router = APIRouter(tags=["Peta"])


@router.get("/polsek", summary="GeoJSON wilayah Polsek + jumlah kasus + zona")
def peta_polsek(
    conn: Conn,
    tahun: int | None = Query(None, description="default: tahun terbaru"),
    jenis: str | None = Query(None, description="id jenis dipisah koma, mis. 1,16"),
    zona: str | None = Query(None, description="tinggi,sedang,rendah"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
):
    daftar_int(jenis, "jenis"), daftar_int(polsek, "polsek"), daftar_zona(zona)   # validasi parameter
    raise belum_diimplementasi("GET /api/polsek")


@router.get("/polsek/{id_polsek}", summary="Detail satu Polsek (untuk popup)")
def detail_polsek(id_polsek: int, conn: Conn, tahun: int | None = None):
    raise belum_diimplementasi("GET /api/polsek/{id}")
