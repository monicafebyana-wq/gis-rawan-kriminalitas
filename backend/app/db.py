"""Koneksi database: connection pool psycopg 3 + dependency FastAPI.

Pemakaian di route:
    from app.db import Conn
    @router.get("/contoh")
    def contoh(conn: Conn):
        rows = conn.execute("SELECT ...", (param,)).fetchall()   # hasil berupa list[dict]
Selalu pakai parameter (%s), JANGAN menyusun SQL dengan f-string (rawan SQL injection).
"""
from typing import Annotated, Iterator

import psycopg
from fastapi import Depends
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from app.config import settings
from app.errors import ApiError

_pool: ConnectionPool | None = None


def buka_pool() -> None:
    """Dipanggil saat aplikasi start. Tidak memblokir/gagal bila DB belum menyala (cek lewat /api/health)."""
    global _pool
    conninfo = make_conninfo(
        host=settings.db_host, port=settings.db_port, dbname=settings.db_name,
        user=settings.db_user, password=settings.db_password,
    )
    _pool = ConnectionPool(
        conninfo, min_size=settings.db_pool_min, max_size=settings.db_pool_max,
        kwargs={"row_factory": dict_row}, open=False, timeout=settings.db_timeout,
    )
    _pool.open(wait=False)


def tutup_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_conn() -> Iterator[psycopg.Connection]:
    """Dependency: pinjam 1 koneksi per request. Transaksi di-commit bila sukses, rollback bila error."""
    if _pool is None:
        raise ApiError(503, "DATABASE_TIDAK_TERSEDIA", "Pool database belum dibuka")
    try:
        with _pool.connection() as conn:
            yield conn
    except PoolTimeout:
        raise ApiError(503, "DATABASE_TIDAK_TERSEDIA",
                       "Tidak bisa terhubung ke database. Pastikan Docker/PostgreSQL menyala dan isi .env benar.")


Conn = Annotated[psycopg.Connection, Depends(get_conn)]
