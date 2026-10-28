"""Login & identitas. Lihat api-contract.md bagian 3.1-3.3."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app import ratelimit, security
from app.config import settings
from app.db import Conn
from app.deps import Pengguna
from app.errors import ApiError, validasi_gagal
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


@router.post("/login", summary="Login admin/operator")
def login(body: LoginBody, request: Request, conn: Conn):
    ip = request.client.host if request.client else "tidak-diketahui"
    ratelimit.periksa(ip, body.username)          # terlalu banyak gagal -> 429 sebelum password dicek
    row = conn.execute("SELECT id_pengguna, username, password_hash, peran FROM pengguna WHERE username = %s",
                       (body.username,)).fetchone()
    # selalu verifikasi hash (palsu bila user tidak ada) -> waktu respons sama, pesan error sama
    valid = security.cocok(body.password, row["password_hash"] if row else security.hash_palsu())
    if row is None or not valid:
        ratelimit.catat_gagal(ip, body.username)
        raise ApiError(401, "TIDAK_TERAUTENTIKASI", "Username atau password salah")
    ratelimit.reset(ip, body.username)
    return {
        "token": security.buat_token(row["id_pengguna"], row["peran"]),
        "tipe": "Bearer",
        "berlaku_detik": settings.jwt_berlaku_detik,
        "pengguna": {"id_pengguna": row["id_pengguna"], "username": row["username"], "peran": row["peran"]},
    }


@router.get("/me", summary="Identitas pengguna yang sedang login")
def me(user: Pengguna):
    return user


class UbahPasswordBody(BaseModel):
    password_lama: str = Field(min_length=1, max_length=200)
    password_baru: str = Field(min_length=8, max_length=72)


@router.post("/ubah-password", status_code=204, summary="Ganti password akun sendiri")
def ubah_password(body: UbahPasswordBody, conn: Conn, user: Pengguna):
    if len(body.password_baru.encode("utf-8")) > security.MAKS_BYTE_PASSWORD:
        raise validasi_gagal(f"Password maksimal {security.MAKS_BYTE_PASSWORD} byte", ["password_baru"])
    row = conn.execute("SELECT password_hash FROM pengguna WHERE id_pengguna = %s", (user["id_pengguna"],)).fetchone()
    if not security.cocok(body.password_lama, row["password_hash"]):
        raise validasi_gagal("Password lama salah", ["password_lama"])        # 400, bukan 401, agar front end tidak mengira token habis
    conn.execute("UPDATE pengguna SET password_hash = %s WHERE id_pengguna = %s",
                 (security.hash_password(body.password_baru), user["id_pengguna"]))
    audit.catat(conn, user, "ubah_password", "pengguna", user["id_pengguna"], {"username": user["username"]})
    return Response(status_code=204)
