"""Data referensi: GET /api/jenis, GET /api/tahun (publik) + kelola jenis kejahatan (POST/PUT/DELETE, khusus admin).

Catatan: 18 jenis BAKU (lihat impor_csv.KOLOM_JENIS) dipakai impor CSV -> tidak boleh dihapus / diganti kodenya.
Jenis baru yang ditambahkan lewat sini diisi per kasus (POST/PUT /api/kasus), bukan lewat impor CSV."""
import psycopg
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.db import Conn
from app.deps import Admin
from app.errors import ApiError, tidak_ditemukan, validasi_gagal
from app.services import audit
from app.services.impor_csv import KOLOM_JENIS

router = APIRouter(tags=["Referensi"])
_BAKU = {kode for _, kode in KOLOM_JENIS}
_KOLOM = "id_jenis, kode_jenis, nama_jenis"


class JenisBaru(BaseModel):
    kode_jenis: str = Field(pattern=r"^[A-Z0-9_]{2,30}$", description="huruf besar/angka/_ , mis. NARKOBA")
    nama_jenis: str = Field(min_length=2, max_length=100)


class JenisUbah(BaseModel):
    kode_jenis: str | None = Field(None, pattern=r"^[A-Z0-9_]{2,30}$")
    nama_jenis: str | None = Field(None, min_length=2, max_length=100)


@router.get("/jenis", summary="Daftar jenis kejahatan")
def daftar_jenis(conn: Conn):
    rows = conn.execute(f"SELECT {_KOLOM} FROM jenis_kejahatan ORDER BY id_jenis").fetchall()
    return {"data": rows}


@router.get("/tahun", summary="Tahun yang tersedia datanya")
def daftar_tahun(conn: Conn):
    tahun = [r["tahun"] for r in conn.execute("SELECT DISTINCT tahun FROM kasus_kejahatan ORDER BY tahun").fetchall()]
    return {"data": tahun, "terbaru": tahun[-1] if tahun else None}


@router.post("/jenis", status_code=201, summary="Tambah jenis kejahatan (khusus admin)")
def tambah_jenis(body: JenisBaru, conn: Conn, user: Admin):
    row = conn.execute(f"INSERT INTO jenis_kejahatan (kode_jenis, nama_jenis) VALUES (%s, %s) ON CONFLICT (kode_jenis) DO NOTHING RETURNING {_KOLOM}",
                       (body.kode_jenis, body.nama_jenis)).fetchone()
    if row is None:
        raise ApiError(409, "DATA_SUDAH_ADA", f"Kode jenis '{body.kode_jenis}' sudah dipakai")
    audit.catat(conn, user, "tambah", "jenis", row["id_jenis"], row)
    conn.commit()
    return row


@router.put("/jenis/{id_jenis}", summary="Ubah jenis kejahatan (khusus admin)")
def ubah_jenis(id_jenis: int, body: JenisUbah, conn: Conn, user: Admin):
    diubah = body.model_dump(exclude_none=True)
    if not diubah:
        raise validasi_gagal("Isi minimal satu field: kode_jenis atau nama_jenis", ["kode_jenis", "nama_jenis"])
    lama = conn.execute(f"SELECT {_KOLOM} FROM jenis_kejahatan WHERE id_jenis = %s FOR UPDATE", (id_jenis,)).fetchone()
    if lama is None:
        raise tidak_ditemukan(f"Jenis dengan id {id_jenis} tidak ditemukan")
    if lama["kode_jenis"] in _BAKU and diubah.get("kode_jenis", lama["kode_jenis"]) != lama["kode_jenis"]:
        raise ApiError(409, "AKSI_DITOLAK", "Kode jenis baku dipakai impor CSV dan tidak boleh diganti (nama_jenis boleh)")
    set_sql = ", ".join(f"{k} = %({k})s" for k in diubah)
    try:
        row = conn.execute(f"UPDATE jenis_kejahatan SET {set_sql} WHERE id_jenis = %(id)s RETURNING {_KOLOM}", {**diubah, "id": id_jenis}).fetchone()
    except psycopg.errors.UniqueViolation:
        raise ApiError(409, "DATA_SUDAH_ADA", f"Kode jenis '{diubah.get('kode_jenis')}' sudah dipakai")
    audit.catat(conn, user, "ubah", "jenis", id_jenis, {"sebelum": lama, "sesudah": row})
    conn.commit()
    return row


@router.delete("/jenis/{id_jenis}", status_code=204, summary="Hapus jenis kejahatan (khusus admin; hanya jenis non-baku tanpa kasus)")
def hapus_jenis(id_jenis: int, conn: Conn, user: Admin):
    lama = conn.execute(f"SELECT {_KOLOM} FROM jenis_kejahatan WHERE id_jenis = %s", (id_jenis,)).fetchone()
    if lama is None:
        raise tidak_ditemukan(f"Jenis dengan id {id_jenis} tidak ditemukan")
    if lama["kode_jenis"] in _BAKU:
        raise ApiError(409, "AKSI_DITOLAK", "Jenis baku dipakai impor CSV dan tidak boleh dihapus")
    try:
        conn.execute("DELETE FROM jenis_kejahatan WHERE id_jenis = %s", (id_jenis,))
    except psycopg.errors.ForeignKeyViolation:
        raise ApiError(409, "AKSI_DITOLAK", "Jenis masih punya data kasus. Hapus atau pindahkan kasusnya dulu.")
    audit.catat(conn, user, "hapus", "jenis", id_jenis, lama)
    conn.commit()
    return Response(status_code=204)
