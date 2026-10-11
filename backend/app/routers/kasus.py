"""Data tabel kasus + CRUD admin. TODO: GET (No 18), POST/PUT/DELETE (No 26). Lihat api-contract.md bagian 2.5 & 3.4."""
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.db import Conn
from app.errors import belum_diimplementasi
from app.params import daftar_int

router = APIRouter(tags=["Kasus"])


class KasusBaru(BaseModel):
    id_polsek: int
    id_jenis: int
    tahun: int
    jumlah: int = Field(ge=0)


class KasusUbah(BaseModel):
    jumlah: int = Field(ge=0)


@router.get("/kasus", summary="Daftar kasus (paginasi)")
def daftar_kasus(
    conn: Conn,
    tahun: int | None = None,
    polsek: str | None = None,
    jenis: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    daftar_int(polsek, "polsek"), daftar_int(jenis, "jenis")
    raise belum_diimplementasi("GET /api/kasus")


@router.post("/kasus", status_code=201, summary="Tambah kasus (operator/admin)")
def tambah_kasus(body: KasusBaru, conn: Conn):
    raise belum_diimplementasi("POST /api/kasus")


@router.put("/kasus/{id_kasus}", summary="Ubah jumlah kasus (operator/admin)")
def ubah_kasus(id_kasus: int, body: KasusUbah, conn: Conn):
    raise belum_diimplementasi("PUT /api/kasus/{id}")


@router.delete("/kasus/{id_kasus}", status_code=204, summary="Hapus kasus (khusus admin)")
def hapus_kasus(id_kasus: int, conn: Conn):
    raise belum_diimplementasi("DELETE /api/kasus/{id}")
