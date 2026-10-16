"""Hash password (bcrypt) dan token JWT."""
import functools
import time

import bcrypt
import jwt

from app.config import settings

MAKS_BYTE_PASSWORD = 72          # batas bcrypt


def hash_password(password: str) -> str:
    b = password.encode("utf-8")
    if len(b) > MAKS_BYTE_PASSWORD:
        raise ValueError(f"Password maksimal {MAKS_BYTE_PASSWORD} byte")
    return bcrypt.hashpw(b, bcrypt.gensalt(rounds=settings.bcrypt_rounds)).decode("ascii")


def cocok(password: str, hashed: str) -> bool:
    b = password.encode("utf-8")
    if len(b) > MAKS_BYTE_PASSWORD:
        return False
    try:
        return bcrypt.checkpw(b, hashed.encode("ascii"))
    except ValueError:               # hash di DB rusak
        return False


@functools.cache
def hash_palsu() -> str:
    """Dipakai saat username tidak ada, supaya waktu respons login sama (tidak membocorkan username yang valid)."""
    return hash_password("password-palsu-untuk-penyamaran")


def buat_token(id_pengguna: int, peran: str) -> str:
    sekarang = int(time.time())
    return jwt.encode({"sub": str(id_pengguna), "peran": peran, "iat": sekarang, "exp": sekarang + settings.jwt_berlaku_detik},
                      settings.jwt_secret, algorithm="HS256")


def baca_token(token: str) -> dict:
    """Melempar jwt.PyJWTError bila token palsu/kedaluwarsa."""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
