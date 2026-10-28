"""Titik masuk aplikasi.  Jalankan dari folder backend/:
    uvicorn app.main:app --reload --port 3000
Dokumentasi interaktif otomatis: http://localhost:3000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__, db
from app.config import settings
from app.errors import daftar_handler
from app.routers import audit, auth, health, kasus, laporan, pengguna, polsek, referensi, spasial, statistik, titik


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.jwt_secret == "ganti_dengan_string_acak":
        logging.getLogger("uvicorn.error").warning("JWT_SECRET masih nilai bawaan - ganti di .env sebelum dipakai sungguhan")
    db.buka_pool()
    yield
    db.tutup_pool()


app = FastAPI(
    title="API Web GIS Rawan Kriminalitas",
    description="Implementasi docs/api-contract.md",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Content-Disposition", "Retry-After"],       # agar JavaScript front end boleh membacanya (unduhan & 429)
)
daftar_handler(app)

api = APIRouter(prefix="/api")
for r in (health.router, referensi.router, polsek.router, kasus.router, statistik.router, auth.router, pengguna.router, audit.router, spasial.router, titik.router, laporan.router):
    api.include_router(r)
app.include_router(api)
