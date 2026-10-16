"""Login & identitas. Lihat api-contract.md bagian 3.1-3.3."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import security
from app.config import settings
from app.db import Conn
from app.deps import Pengguna
from app.errors import ApiError

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login", summary="Login admin/operator")
def login(body: LoginBody, conn: Conn):
    row = conn.execute("SELECT id_pengguna, username, password_hash, peran FROM pengguna WHERE username = %s",
                       (body.username,)).fetchone()
    # selalu verifikasi hash (palsu bila user tidak ada) -> waktu respons sama, pesan error sama
    valid = security.cocok(body.password, row["password_hash"] if row else security.hash_palsu())
    if row is None or not valid:
        raise ApiError(401, "TIDAK_TERAUTENTIKASI", "Username atau password salah")
    return {
        "token": security.buat_token(row["id_pengguna"], row["peran"]),
        "tipe": "Bearer",
        "berlaku_detik": settings.jwt_berlaku_detik,
        "pengguna": {"id_pengguna": row["id_pengguna"], "username": row["username"], "peran": row["peran"]},
    }


@router.get("/me", summary="Identitas pengguna yang sedang login")
def me(user: Pengguna):
    return user
