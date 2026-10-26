"""Manajemen akun admin/operator - KHUSUS ADMIN (alur: admin yang sudah ada mendaftarkan akun baru).

  GET    /api/pengguna          daftar akun
  POST   /api/pengguna          daftarkan akun baru (peran: admin / operator)
  PUT    /api/pengguna/{id}     ubah peran dan/atau reset password
  DELETE /api/pengguna/{id}     hapus akun

Admin PERTAMA tetap dibuat lewat CLI:  python -m app.buat_pengguna admin --peran admin
Aturan pengaman: tidak boleh menghapus akun sendiri, dan sistem tidak boleh kehilangan admin terakhir.
"""
from typing import Literal

import psycopg
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app import security
from app.db import Conn
from app.deps import Admin
from app.errors import ApiError, tidak_ditemukan, validasi_gagal

router = APIRouter(prefix="/pengguna", tags=["Pengguna"])

Peran = Literal["admin", "operator"]
_KOLOM = "id_pengguna, username, peran"          # password_hash TIDAK PERNAH dikembalikan


class PenggunaBaru(BaseModel):
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,50}$", description="3-50 karakter: huruf, angka, titik, _ atau -")
    password: str = Field(min_length=8, max_length=72)
    peran: Peran = "operator"                    # default hak terendah; admin harus diminta eksplisit


class PenggunaUbah(BaseModel):
    peran: Peran | None = None
    password: str | None = Field(None, min_length=8, max_length=72, description="isi untuk reset password")


def _cek_password(pw: str) -> None:
    if len(pw.encode("utf-8")) > security.MAKS_BYTE_PASSWORD:       # batas bcrypt dihitung dalam byte, bukan karakter
        raise validasi_gagal(f"Password maksimal {security.MAKS_BYTE_PASSWORD} byte", ["password"])


def _kunci_admin(conn: psycopg.Connection) -> None:
    """Kunci semua baris admin: dua request bersamaan tidak bisa saling menghapus/menurunkan sampai admin habis."""
    conn.execute("SELECT 1 FROM pengguna WHERE peran = 'admin' FOR UPDATE").fetchall()


def _harus_ada_admin(conn: psycopg.Connection) -> None:
    if conn.execute("SELECT 1 FROM pengguna WHERE peran = 'admin' LIMIT 1").fetchone() is None:
        raise ApiError(409, "AKSI_DITOLAK", "Aksi dibatalkan: harus selalu ada minimal satu admin")


@router.get("", summary="Daftar akun (khusus admin)")
def daftar_pengguna(conn: Conn, user: Admin):
    return {"data": conn.execute(f"SELECT {_KOLOM} FROM pengguna ORDER BY id_pengguna").fetchall()}


@router.post("", status_code=201, summary="Daftarkan akun baru (khusus admin)")
def tambah_pengguna(body: PenggunaBaru, conn: Conn, user: Admin):
    _cek_password(body.password)
    row = conn.execute(
        f"""INSERT INTO pengguna (username, password_hash, peran) VALUES (%s, %s, %s)
            ON CONFLICT (username) DO NOTHING RETURNING {_KOLOM}""",
        (body.username, security.hash_password(body.password), body.peran)).fetchone()
    if row is None:
        raise ApiError(409, "DATA_SUDAH_ADA", f"Username '{body.username}' sudah dipakai")
    return row


@router.put("/{id_pengguna}", summary="Ubah peran / reset password (khusus admin)")
def ubah_pengguna(id_pengguna: int, body: PenggunaUbah, conn: Conn, user: Admin):
    if body.peran is None and body.password is None:
        raise validasi_gagal("Isi minimal salah satu: peran atau password", ["peran", "password"])
    if body.password is not None:
        _cek_password(body.password)
    _kunci_admin(conn)
    target = conn.execute("SELECT peran FROM pengguna WHERE id_pengguna = %s FOR UPDATE", (id_pengguna,)).fetchone()
    if target is None:
        raise tidak_ditemukan(f"Pengguna dengan id {id_pengguna} tidak ditemukan")
    peran = body.peran or target["peran"]
    if body.password is not None:
        row = conn.execute(f"UPDATE pengguna SET peran = %s, password_hash = %s WHERE id_pengguna = %s RETURNING {_KOLOM}",
                           (peran, security.hash_password(body.password), id_pengguna)).fetchone()
    else:
        row = conn.execute(f"UPDATE pengguna SET peran = %s WHERE id_pengguna = %s RETURNING {_KOLOM}",
                           (peran, id_pengguna)).fetchone()
    _harus_ada_admin(conn)                       # gagal -> rollback otomatis
    return row


@router.delete("/{id_pengguna}", status_code=204, summary="Hapus akun (khusus admin)")
def hapus_pengguna(id_pengguna: int, conn: Conn, user: Admin):
    if id_pengguna == user["id_pengguna"]:
        raise ApiError(409, "AKSI_DITOLAK", "Tidak bisa menghapus akun sendiri")
    _kunci_admin(conn)
    row = conn.execute("DELETE FROM pengguna WHERE id_pengguna = %s RETURNING id_pengguna", (id_pengguna,)).fetchone()
    if row is None:
        raise tidak_ditemukan(f"Pengguna dengan id {id_pengguna} tidak ditemukan")
    _harus_ada_admin(conn)
    return Response(status_code=204)
