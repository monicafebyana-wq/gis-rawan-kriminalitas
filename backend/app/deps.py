"""Dependency autentikasi & peran.

Pemakaian di endpoint:
    from app.deps import Pengguna, Admin
    def tambah(body: X, conn: Conn, user: Pengguna): ...     # operator ATAU admin
    def hapus(id: int, conn: Conn, user: Admin): ...         # khusus admin
Urutan pengecekan: tidak login -> 401, peran kurang -> 403.
"""
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import security
from app.db import Conn
from app.errors import ApiError

_skema = HTTPBearer(auto_error=False, description="Token dari POST /api/auth/login")


def _tidak_terautentikasi(pesan: str = "Token tidak ada, tidak valid, atau sudah kedaluwarsa") -> ApiError:
    return ApiError(401, "TIDAK_TERAUTENTIKASI", pesan)


def pengguna_saat_ini(conn: Conn, kredensial: HTTPAuthorizationCredentials | None = Depends(_skema)) -> dict:
    if kredensial is None:
        raise _tidak_terautentikasi("Perlu login: kirim header Authorization: Bearer <token>")
    try:
        data = security.baca_token(kredensial.credentials)
        id_pengguna = int(data["sub"])
    except (jwt.PyJWTError, ValueError):
        raise _tidak_terautentikasi()
    # peran dibaca dari DB (bukan dari token) supaya perubahan/penghapusan akun langsung berlaku
    row = conn.execute("SELECT id_pengguna, username, peran FROM pengguna WHERE id_pengguna = %s", (id_pengguna,)).fetchone()
    if row is None:
        raise _tidak_terautentikasi()
    return row


def butuh_admin(user: Annotated[dict, Depends(pengguna_saat_ini)]) -> dict:
    if user["peran"] != "admin":
        raise ApiError(403, "TIDAK_DIIZINKAN", "Hanya admin yang boleh melakukan aksi ini")
    return user


Pengguna = Annotated[dict, Depends(pengguna_saat_ini)]     # operator atau admin
Admin = Annotated[dict, Depends(butuh_admin)]              # khusus admin
