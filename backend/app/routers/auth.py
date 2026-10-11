"""Login & identitas. TODO: tugas "Autentikasi" (No 25). Lihat api-contract.md bagian 3.1-3.3."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.db import Conn
from app.errors import belum_diimplementasi

router = APIRouter(prefix="/auth", tags=["Autentikasi"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/login", summary="Login admin/operator")
def login(body: LoginBody, conn: Conn):
    raise belum_diimplementasi("POST /api/auth/login")


@router.get("/me", summary="Identitas pengguna yang sedang login")
def me(conn: Conn):
    raise belum_diimplementasi("GET /api/auth/me")
