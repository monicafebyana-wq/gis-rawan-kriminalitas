"""Riwayat perubahan data (khusus admin): GET /api/audit"""
from datetime import date

from fastapi import APIRouter, Query

from app.db import Conn
from app.deps import Admin

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", summary="Riwayat perubahan data (khusus admin)")
def daftar_audit(
    conn: Conn, user: Admin,
    entitas: str | None = Query(None, max_length=30, description="kasus / pengguna / polsek / jenis / poligon"),
    aksi: str | None = Query(None, max_length=30, description="tambah / ubah / hapus / impor / ubah_password / ..."),
    username: str | None = Query(None, max_length=50),
    dari: date | None = Query(None, description="YYYY-MM-DD (termasuk)"),
    sampai: date | None = Query(None, description="YYYY-MM-DD (termasuk)"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    where = """(%(entitas)s::text IS NULL OR entitas = %(entitas)s::text)
               AND (%(aksi)s::text IS NULL OR aksi = %(aksi)s::text)
               AND (%(username)s::text IS NULL OR username = %(username)s::text)
               AND (%(dari)s::date IS NULL OR waktu >= %(dari)s::date)
               AND (%(sampai)s::date IS NULL OR waktu < %(sampai)s::date + 1)"""
    prm = {"entitas": entitas, "aksi": aksi, "username": username, "dari": dari, "sampai": sampai,
           "limit": limit, "offset": (page - 1) * limit}
    total = conn.execute(f"SELECT count(*) AS n FROM audit_log WHERE {where}", prm).fetchone()["n"]
    data = conn.execute(
        f"""SELECT id_log, waktu, id_pengguna, username, aksi, entitas, id_entitas, detail
            FROM audit_log WHERE {where} ORDER BY id_log DESC LIMIT %(limit)s OFFSET %(offset)s""", prm).fetchall()
    return {"page": page, "limit": limit, "total_data": total, "data": data}
