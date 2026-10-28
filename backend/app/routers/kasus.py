"""Data tabel kasus (GET publik) + CRUD (POST/PUT: operator/admin, DELETE: khusus admin). Lihat api-contract.md bagian 2.5 & 3.4.
Catatan: f-string di bawah hanya menyisipkan potongan SQL tetap (bukan input pengguna); semua nilai lewat parameter."""
import psycopg
from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from app.db import Conn
from app.deps import Admin, Pengguna
from app.errors import ApiError, tidak_ditemukan, validasi_gagal
from app.params import daftar_int
from app.services import audit, rekap, zonasi

router = APIRouter(tags=["Kasus"])


class KasusBaru(BaseModel):
    id_polsek: int
    id_jenis: int
    tahun: int = Field(ge=2000, le=2100)
    jumlah: int = Field(ge=0)


class KasusUbah(BaseModel):
    """Semua field opsional: kirim hanya yang ingin diubah (minimal satu). Field lain (mis. nama_polsek) diabaikan
    dan disebutkan di respons pada kunci `diabaikan`."""
    model_config = ConfigDict(extra="allow")
    id_polsek: int | None = None
    id_jenis: int | None = None
    tahun: int | None = Field(None, ge=2000, le=2100)
    jumlah: int | None = Field(None, ge=0)


_KOLOM = "id_kasus, id_polsek, id_jenis, tahun, jumlah"
_REFERENSI = {"id_polsek": "polsek", "id_jenis": "jenis_kejahatan"}      # kolom -> tabel (konstanta, bukan input pengguna)


def _cek_referensi(conn, **nilai: int | None) -> None:
    salah = [k for k, v in nilai.items()
             if v is not None and conn.execute(f"SELECT 1 FROM {_REFERENSI[k]} WHERE {k} = %s", (v,)).fetchone() is None]
    if salah:
        raise validasi_gagal("Referensi tidak ditemukan: " + ", ".join(salah), salah)


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
    _cek_referensi(conn, id_polsek=body.id_polsek, id_jenis=body.id_jenis)
    row = conn.execute(
        f"""INSERT INTO kasus_kejahatan (id_polsek, id_jenis, tahun, jumlah) VALUES (%s, %s, %s, %s)
            ON CONFLICT (id_polsek, id_jenis, tahun) DO NOTHING RETURNING {_KOLOM}""",
        (body.id_polsek, body.id_jenis, body.tahun, body.jumlah)).fetchone()
    if row is None:
        raise ApiError(409, "DATA_SUDAH_ADA", "Kombinasi polsek+jenis+tahun sudah ada (pakai PUT /kasus/{id} untuk mengubahnya)")
    zonasi.refresh_zona(conn, body.tahun)
    audit.catat(conn, user, "tambah", "kasus", row["id_kasus"], row)
    conn.commit()
    return row


@router.put("/kasus/{id_kasus}", summary="Ubah kasus - semua field boleh diubah (operator/admin)")
def ubah_kasus(id_kasus: int, body: KasusUbah, conn: Conn, user: Pengguna):
    perubahan = {k: v for k, v in body.model_dump(exclude_none=True).items() if k in KasusUbah.model_fields}   # hanya kolom resmi
    if not perubahan:
        raise validasi_gagal("Kirim minimal satu field yang ingin diubah", list(KasusUbah.model_fields))
    lama = conn.execute(f"SELECT {_KOLOM} FROM kasus_kejahatan WHERE id_kasus = %s FOR UPDATE", (id_kasus,)).fetchone()
    if lama is None:
        raise tidak_ditemukan(f"Kasus dengan id {id_kasus} tidak ditemukan")
    _cek_referensi(conn, id_polsek=perubahan.get("id_polsek"), id_jenis=perubahan.get("id_jenis"))
    set_sql = ", ".join(f"{k} = %({k})s" for k in perubahan)               # nama kolom dari model (tetap); nilai lewat parameter
    try:
        row = conn.execute(f"UPDATE kasus_kejahatan SET {set_sql} WHERE id_kasus = %(id_kasus)s RETURNING {_KOLOM}",
                           {**perubahan, "id_kasus": id_kasus}).fetchone()
    except psycopg.errors.UniqueViolation:
        raise ApiError(409, "DATA_SUDAH_ADA", "Kombinasi polsek+jenis+tahun itu sudah dipakai data kasus lain")
    for t in {lama["tahun"], row["tahun"]}:                                 # tahun lama & baru sama-sama dihitung ulang zonanya
        zonasi.refresh_zona(conn, t)
    audit.catat(conn, user, "ubah", "kasus", id_kasus, {"sebelum": lama, "sesudah": row})
    conn.commit()
    # `diubah` = field yang nilainya benar-benar berbeda; `diabaikan` = field kiriman yang bukan kolom kasus
    return {**row, "diubah": sorted(k for k in perubahan if perubahan[k] != lama[k]), "diabaikan": sorted(body.model_extra or {})}


@router.delete("/kasus/{id_kasus}", status_code=204, summary="Hapus kasus (khusus admin)")
def hapus_kasus(id_kasus: int, conn: Conn, user: Admin):
    row = conn.execute(f"DELETE FROM kasus_kejahatan WHERE id_kasus = %s RETURNING {_KOLOM}", (id_kasus,)).fetchone()
    if row is None:
        raise tidak_ditemukan(f"Kasus dengan id {id_kasus} tidak ditemukan")
    zonasi.refresh_zona(conn, row["tahun"])
    audit.catat(conn, user, "hapus", "kasus", id_kasus, row)
    conn.commit()
    return Response(status_code=204)
