"""Data tabel kasus (GET publik) + CRUD (POST/PUT: operator/admin, DELETE: khusus admin). Lihat api-contract.md bagian 2.5 & 3.4.
Catatan: f-string di bawah hanya menyisipkan potongan SQL tetap (bukan input pengguna); semua nilai lewat parameter."""
from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, Field

from app.db import Conn
from app.deps import Admin, Pengguna
from app.errors import ApiError, tidak_ditemukan, validasi_gagal
from app.params import daftar_int
from app.services import rekap, zonasi

router = APIRouter(tags=["Kasus"])


class KasusBaru(BaseModel):
    id_polsek: int
    id_jenis: int
    tahun: int = Field(ge=2000, le=2100)
    jumlah: int = Field(ge=0)


class KasusUbah(BaseModel):
    jumlah: int = Field(ge=0)


_KOLOM = "id_kasus, id_polsek, id_jenis, tahun, jumlah"


@router.get("/kasus", summary="Daftar kasus (paginasi)")
def daftar_kasus(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
    jenis: str | None = Query(None, description="id jenis dipisah koma"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    polsek_l, jenis_l = daftar_int(polsek, "polsek"), daftar_int(jenis, "jenis")
    t = tahun if tahun is not None else rekap.tahun_terbaru(conn)
    if t is None:                                           # DB masih kosong -> daftar kosong, bukan error
        return {"page": page, "limit": limit, "total_data": 0, "data": []}
    where = """k.tahun = %(tahun)s
               AND (%(polsek)s::int[] IS NULL OR k.id_polsek = ANY(%(polsek)s::int[]))
               AND (%(jenis)s::int[]  IS NULL OR k.id_jenis  = ANY(%(jenis)s::int[]))"""
    prm = {"tahun": t, "polsek": polsek_l, "jenis": jenis_l, "limit": limit, "offset": (page - 1) * limit}
    total = conn.execute(f"SELECT count(*) AS n FROM kasus_kejahatan k WHERE {where}", prm).fetchone()["n"]
    data = conn.execute(
        f"""SELECT k.id_kasus, k.id_polsek, p.nama_polsek, k.id_jenis, j.nama_jenis, k.tahun, k.jumlah
            FROM kasus_kejahatan k
            JOIN polsek p USING (id_polsek) JOIN jenis_kejahatan j USING (id_jenis)
            WHERE {where} ORDER BY k.id_kasus LIMIT %(limit)s OFFSET %(offset)s""", prm).fetchall()
    return {"page": page, "limit": limit, "total_data": total, "data": data}


@router.post("/kasus", status_code=201, summary="Tambah kasus (operator/admin)")
def tambah_kasus(body: KasusBaru, conn: Conn, user: Pengguna):
    salah = [n for n, tabel, kolom, nilai in (("id_polsek", "polsek", "id_polsek", body.id_polsek),
                                              ("id_jenis", "jenis_kejahatan", "id_jenis", body.id_jenis))
             if conn.execute(f"SELECT 1 FROM {tabel} WHERE {kolom} = %s", (nilai,)).fetchone() is None]
    if salah:
        raise validasi_gagal("Referensi tidak ditemukan: " + ", ".join(salah), salah)
    row = conn.execute(
        f"""INSERT INTO kasus_kejahatan (id_polsek, id_jenis, tahun, jumlah) VALUES (%s, %s, %s, %s)
            ON CONFLICT (id_polsek, id_jenis, tahun) DO NOTHING RETURNING {_KOLOM}""",
        (body.id_polsek, body.id_jenis, body.tahun, body.jumlah)).fetchone()
    if row is None:
        raise ApiError(409, "DATA_SUDAH_ADA", "Kombinasi polsek+jenis+tahun sudah ada (pakai PUT untuk mengubah jumlahnya)")
    zonasi.refresh_zona(conn, body.tahun)
    conn.commit()
    return row


@router.put("/kasus/{id_kasus}", summary="Ubah jumlah kasus (operator/admin)")
def ubah_kasus(id_kasus: int, body: KasusUbah, conn: Conn, user: Pengguna):
    row = conn.execute(f"UPDATE kasus_kejahatan SET jumlah = %s WHERE id_kasus = %s RETURNING {_KOLOM}",
                       (body.jumlah, id_kasus)).fetchone()
    if row is None:
        raise tidak_ditemukan(f"Kasus dengan id {id_kasus} tidak ditemukan")
    zonasi.refresh_zona(conn, row["tahun"])
    conn.commit()
    return row


@router.delete("/kasus/{id_kasus}", status_code=204, summary="Hapus kasus (khusus admin)")
def hapus_kasus(id_kasus: int, conn: Conn, user: Admin):
    row = conn.execute("DELETE FROM kasus_kejahatan WHERE id_kasus = %s RETURNING tahun", (id_kasus,)).fetchone()
    if row is None:
        raise tidak_ditemukan(f"Kasus dengan id {id_kasus} tidak ditemukan")
    zonasi.refresh_zona(conn, row["tahun"])
    conn.commit()
    return Response(status_code=204)
