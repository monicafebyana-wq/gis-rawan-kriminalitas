"""Peta utama & popup (GET publik) + kelola master Polsek & poligon wilayah (khusus admin).
Lihat docs/api-contract.md bagian 2.1 dan 2.2."""
from fastapi import APIRouter, Body, File, Form, Query, Response, UploadFile
import psycopg
from pydantic import BaseModel, Field

from app.db import Conn
from app.deps import Admin
from app.errors import ApiError, tidak_ditemukan, validasi_gagal
from app.params import daftar_int, daftar_zona
from app.services import audit, geojson_polsek, rekap, zonasi
from app.services.impor_csv import normalkan_nama

router = APIRouter(tags=["Peta"])
_KOLOM = "id_polsek, nama_polsek, nama_wilayah_resmi, (geom IS NOT NULL) AS punya_poligon"


class PolsekBaru(BaseModel):
    nama_polsek: str = Field(min_length=3, max_length=100, description="mis. 'Soreang' (awalan 'Polsek' dibuang otomatis)")
    nama_wilayah_resmi: str | None = Field(None, max_length=100, description="nama kecamatan (opsional)")


class PolsekUbah(BaseModel):
    nama_polsek: str | None = Field(None, min_length=3, max_length=100)
    nama_wilayah_resmi: str | None = Field(None, max_length=100, description="kirim null untuk mengosongkan")


def _nama_valid(nama: str, kecuali_id: int | None = None, conn: Conn | None = None) -> str:
    n = normalkan_nama(nama)
    if len(n) < 3:
        raise validasi_gagal("nama_polsek minimal 3 karakter (di luar awalan 'Polsek')", ["nama_polsek"])
    if conn is not None and conn.execute("SELECT 1 FROM polsek WHERE lower(nama_polsek) = lower(%s) AND id_polsek IS DISTINCT FROM %s",
                                         (n, kecuali_id)).fetchone():
        raise ApiError(409, "DATA_SUDAH_ADA", f"Polsek '{n}' sudah ada")
    return n


# ---------------------------------------------------------------- peta (publik)
@router.get("/polsek", summary="GeoJSON wilayah Polsek + jumlah kasus + zona")
def peta_polsek(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru"),
    jenis: str | None = Query(None, description="id jenis dipisah koma, mis. 1,16"),
    zona: str | None = Query(None, description="tinggi,sedang,rendah (dipisah koma)"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
):
    jenis_l, polsek_l, zona_l = daftar_int(jenis, "jenis"), daftar_int(polsek, "polsek"), daftar_zona(zona)
    t = rekap.tentukan_tahun(conn, tahun)
    rows = rekap.rekap_per_polsek(conn, t, jenis_l, polsek_l, zona_l, dengan_geom=True)
    return {"type": "FeatureCollection", "features": rekap.fitur_geojson(rows, t)}


# ---------------------------------------------------------------- poligon (admin) - didaftarkan SEBELUM /polsek/{id}
@router.post("/polsek/geojson", summary="Unggah poligon wilayah dari GeoJSON (khusus admin)")
def unggah_geojson(
    conn: Conn, user: Admin,
    file: UploadFile = File(..., description="GeoJSON FeatureCollection; tiap feature: properties.id_polsek (atau nama_polsek) + Polygon/MultiPolygon WGS 84"),
    dry_run: bool = Form(False, description="true = hanya validasi, tidak menyimpan"),
):
    isi = file.file.read(geojson_polsek.MAKS_BYTE + 1)
    hasil = geojson_polsek.terapkan(conn, geojson_polsek.baca_fitur(isi), dry_run)
    if not dry_run:
        audit.catat(conn, user, "impor", "poligon", None, {"berkas": file.filename, "polsek": [p["id_polsek"] for p in hasil["polsek_diperbarui"]]})
        conn.commit()
    return hasil


@router.put("/polsek/{id_polsek}/poligon", summary="Ganti poligon satu Polsek (khusus admin)")
def ganti_poligon(id_polsek: int, conn: Conn, user: Admin,
                  geometri: dict = Body(..., description="objek geometri GeoJSON (Polygon/MultiPolygon) atau Feature"),
                  dry_run: bool = Query(False)):
    if geometri.get("type") == "Feature":
        geometri = geometri.get("geometry") or {}
    hasil = geojson_polsek.terapkan(conn, [{"type": "Feature", "properties": {"id_polsek": id_polsek}, "geometry": geometri}], dry_run) \
        if conn.execute("SELECT 1 FROM polsek WHERE id_polsek = %s", (id_polsek,)).fetchone() else None
    if hasil is None:
        raise tidak_ditemukan(f"Polsek dengan id {id_polsek} tidak ditemukan")
    if not dry_run:
        audit.catat(conn, user, "ubah", "poligon", id_polsek, {"tipe": geometri.get("type")})
        conn.commit()
    return hasil


# ---------------------------------------------------------------- master Polsek (admin)
@router.post("/polsek", status_code=201, summary="Tambah Polsek (khusus admin)")
def tambah_polsek(body: PolsekBaru, conn: Conn, user: Admin):
    nama = _nama_valid(body.nama_polsek, None, conn)
    row = conn.execute(f"INSERT INTO polsek (nama_polsek, nama_wilayah_resmi) VALUES (%s, %s) RETURNING {_KOLOM}",
                       (nama, body.nama_wilayah_resmi)).fetchone()
    zonasi.refresh_zona(conn)                                # Polsek baru langsung punya baris zona (total 0) di tiap tahun
    audit.catat(conn, user, "tambah", "polsek", row["id_polsek"], row)
    conn.commit()
    return row


@router.put("/polsek/{id_polsek}", summary="Ubah nama Polsek (khusus admin)")
def ubah_polsek(id_polsek: int, body: PolsekUbah, conn: Conn, user: Admin):
    diubah = body.model_dump(exclude_unset=True)
    if not diubah or ("nama_polsek" in diubah and diubah["nama_polsek"] is None):
        raise validasi_gagal("Isi minimal satu field (nama_polsek tidak boleh null)", ["nama_polsek", "nama_wilayah_resmi"])
    lama = conn.execute(f"SELECT {_KOLOM} FROM polsek WHERE id_polsek = %s FOR UPDATE", (id_polsek,)).fetchone()
    if lama is None:
        raise tidak_ditemukan(f"Polsek dengan id {id_polsek} tidak ditemukan")
    if "nama_polsek" in diubah:
        diubah["nama_polsek"] = _nama_valid(diubah["nama_polsek"], id_polsek, conn)
    set_sql = ", ".join(f"{k} = %({k})s" for k in diubah)          # kolom dari model (tetap); nilai lewat parameter
    row = conn.execute(f"UPDATE polsek SET {set_sql} WHERE id_polsek = %(id)s RETURNING {_KOLOM}", {**diubah, "id": id_polsek}).fetchone()
    audit.catat(conn, user, "ubah", "polsek", id_polsek, {"sebelum": lama, "sesudah": row})
    conn.commit()
    return row


@router.delete("/polsek/{id_polsek}", status_code=204, summary="Hapus Polsek (khusus admin; hanya bila tanpa data kasus)")
def hapus_polsek(id_polsek: int, conn: Conn, user: Admin):
    try:
        row = conn.execute(f"DELETE FROM polsek WHERE id_polsek = %s RETURNING {_KOLOM}", (id_polsek,)).fetchone()
    except psycopg.errors.ForeignKeyViolation:
        raise ApiError(409, "AKSI_DITOLAK", "Polsek masih punya data kasus. Hapus atau pindahkan kasusnya dulu (PUT /api/kasus/{id}).")
    if row is None:
        raise tidak_ditemukan(f"Polsek dengan id {id_polsek} tidak ditemukan")
    audit.catat(conn, user, "hapus", "polsek", id_polsek, row)
    conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- popup (publik)
@router.get("/polsek/{id_polsek}", summary="Detail satu Polsek (untuk popup)")
def detail_polsek(id_polsek: int, conn: Conn, tahun: int | None = Query(None, ge=2000, le=2100)):
    t = rekap.tentukan_tahun(conn, tahun)
    r = rekap.rekap_per_polsek(conn, t, polsek=[id_polsek])
    if not r:
        raise tidak_ditemukan(f"Polsek dengan id {id_polsek} tidak ditemukan")
    r = r[0]
    rincian = conn.execute(
        """SELECT j.id_jenis, j.kode_jenis, j.nama_jenis, k.jumlah
           FROM kasus_kejahatan k JOIN jenis_kejahatan j USING (id_jenis)
           WHERE k.id_polsek = %s AND k.tahun = %s AND k.jumlah > 0
           ORDER BY k.jumlah DESC, j.id_jenis""", (id_polsek, t)).fetchall()
    return {"id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "tahun": t,
            "total_kasus": r["total_semua_jenis"], "kategori_zona": r["kategori_zona"], "rincian_jenis": rincian}
