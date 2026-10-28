"""Titik kejadian (lat/lng per kejadian) untuk HEATMAP. Tabel terpisah dari rekap kasus -> tidak mengubah jumlah kasus / zona.

  GET    /api/heatmap        PUBLIK  titik dirangkum per sel grid -> [{lat, lng, bobot}]  (koordinat persis tidak dibuka)
  GET    /api/titik          login   daftar titik persis (paginasi)
  POST   /api/titik          operator/admin
  POST   /api/titik/import   operator/admin  (CSV, dry_run)
  PUT    /api/titik/{id}     operator/admin  (semua field boleh diubah)
  DELETE /api/titik/{id}     khusus admin
id_polsek diisi OTOMATIS dari poligon wilayah (NULL bila titik di luar semua wilayah / poligon belum diunggah).
"""
from datetime import date

from fastapi import APIRouter, File, Form, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app.db import Conn
from app.deps import Admin, Pengguna
from app.errors import tidak_ditemukan, validasi_gagal
from app.params import daftar_int
from app.services import audit, titik_csv
from app.services.geojson_polsek import BATAS_WILAYAH
from app.services.titik_csv import TGL_MAX, TGL_MIN

router = APIRouter(tags=["Titik kejadian"])
GRID_MIN = 0.0005                    # ~55 m: sel grid terkecil yang boleh diminta publik

_DARI = "titik_kejadian t LEFT JOIN polsek p ON p.id_polsek = t.id_polsek JOIN jenis_kejahatan j ON j.id_jenis = t.id_jenis"
_KOLOM = """t.id_titik, ST_Y(t.geom)::float8 AS lat, ST_X(t.geom)::float8 AS lng, t.id_polsek, p.nama_polsek,
            t.id_jenis, j.nama_jenis, t.tanggal"""
_WHERE = """(%(tahun)s::int IS NULL OR (t.tanggal >= make_date(%(tahun)s::int, 1, 1) AND t.tanggal < make_date(%(tahun)s::int + 1, 1, 1)))
            AND (%(dari)s::date IS NULL OR t.tanggal >= %(dari)s::date)
            AND (%(sampai)s::date IS NULL OR t.tanggal <= %(sampai)s::date)
            AND (%(jenis)s::int[] IS NULL OR t.id_jenis = ANY(%(jenis)s::int[]))
            AND (%(polsek)s::int[] IS NULL OR t.id_polsek = ANY(%(polsek)s::int[]))"""


class TitikBaru(BaseModel):
    lat: float = Field(ge=-90, le=90, description="lintang, mis. -7.02")
    lng: float = Field(ge=-180, le=180, description="bujur, mis. 107.52")
    id_jenis: int
    tanggal: date = Field(ge=TGL_MIN, le=TGL_MAX)
    id_polsek: int | None = Field(None, description="kosong = otomatis dari poligon wilayah")


class TitikUbah(BaseModel):
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    id_jenis: int | None = None
    tanggal: date | None = Field(None, ge=TGL_MIN, le=TGL_MAX)
    id_polsek: int | None = Field(None, description="kirim null = hitung ulang otomatis dari lokasi")


def _cek_wilayah(lat: float, lng: float) -> None:
    x0, y0, x1, y1 = BATAS_WILAYAH
    if not (x0 <= lng <= x1 and y0 <= lat <= y1):
        raise validasi_gagal(f"Koordinat di luar kotak wilayah (lng {x0}-{x1}, lat {y0} s/d {y1}) - lat/lng tertukar?", ["lat", "lng"])


def _cek_referensi(conn, id_jenis: int | None, id_polsek: int | None) -> None:
    salah = []
    if id_jenis is not None and conn.execute("SELECT 1 FROM jenis_kejahatan WHERE id_jenis = %s", (id_jenis,)).fetchone() is None:
        salah.append("id_jenis")
    if id_polsek is not None and conn.execute("SELECT 1 FROM polsek WHERE id_polsek = %s", (id_polsek,)).fetchone() is None:
        salah.append("id_polsek")
    if salah:
        raise validasi_gagal("Referensi tidak ditemukan: " + ", ".join(salah), salah)


def _polsek_dari_titik(conn, lng: float, lat: float) -> int | None:
    r = conn.execute("""SELECT id_polsek FROM polsek WHERE geom IS NOT NULL AND ST_Covers(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                        ORDER BY id_polsek LIMIT 1""", (lng, lat)).fetchone()
    return r["id_polsek"] if r else None


def _ambil(conn, id_titik: int) -> dict | None:
    return conn.execute(f"SELECT {_KOLOM} FROM {_DARI} WHERE t.id_titik = %s", (id_titik,)).fetchone()


def _filter(tahun, dari, sampai, jenis, polsek) -> dict:
    return {"tahun": tahun, "dari": dari, "sampai": sampai, "jenis": daftar_int(jenis, "jenis"), "polsek": daftar_int(polsek, "polsek")}


# ---------------------------------------------------------------- heatmap (publik)
@router.get("/heatmap", summary="Data heatmap: titik kejadian dirangkum per sel grid")
def heatmap(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="kosong = semua tahun"),
    dari: date | None = Query(None, description="YYYY-MM-DD"),
    sampai: date | None = Query(None, description="YYYY-MM-DD"),
    jenis: str | None = Query(None, description="id jenis dipisah koma"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
    grid: float = Query(0.002, ge=GRID_MIN, le=0.1, description="ukuran sel dalam derajat (0.001 ~ 110 m). Titik dalam satu sel dijumlahkan jadi `bobot`"),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek), "grid": grid}
    rows = conn.execute(
        f"""SELECT ST_Y(s)::float8 AS lat, ST_X(s)::float8 AS lng, count(*)::int AS bobot
            FROM (SELECT ST_SnapToGrid(t.geom, %(grid)s::float8) AS s FROM titik_kejadian t WHERE {_WHERE}) q
            GROUP BY s ORDER BY bobot DESC, lat, lng""", prm).fetchall()
    data = [{"lat": round(r["lat"], 6), "lng": round(r["lng"], 6), "bobot": r["bobot"]} for r in rows]
    return {"grid_derajat": grid, "total_titik": sum(d["bobot"] for d in data), "maks_bobot": data[0]["bobot"] if data else 0, "data": data}


# ---------------------------------------------------------------- titik persis (login)
@router.get("/titik", summary="Daftar titik kejadian persis (operator/admin)")
def daftar_titik(
    conn: Conn, user: Pengguna,
    tahun: int | None = Query(None, ge=2000, le=2100), dari: date | None = Query(None), sampai: date | None = Query(None),
    jenis: str | None = Query(None), polsek: str | None = Query(None),
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek), "limit": limit, "offset": (page - 1) * limit}
    total = conn.execute(f"SELECT count(*) AS n FROM titik_kejadian t WHERE {_WHERE}", prm).fetchone()["n"]
    data = conn.execute(f"SELECT {_KOLOM} FROM {_DARI} WHERE {_WHERE} ORDER BY t.id_titik DESC LIMIT %(limit)s OFFSET %(offset)s", prm).fetchall()
    return {"page": page, "limit": limit, "total_data": total, "data": data}


@router.post("/titik/import", summary="Impor titik kejadian dari CSV (operator/admin)")
def impor_titik(
    conn: Conn, user: Pengguna,
    file: UploadFile = File(..., description="CSV dengan kolom lat, lng, jenis, tanggal"),
    dry_run: bool = Form(False, description="true = hanya validasi, tidak menyimpan"),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise validasi_gagal("Berkas harus berekstensi .csv", ["file"])
    jenis_db: dict[str, int] = {}
    for j in conn.execute("SELECT id_jenis, kode_jenis, nama_jenis FROM jenis_kejahatan").fetchall():
        jenis_db[j["kode_jenis"].upper()] = jenis_db[j["nama_jenis"].lower()] = j["id_jenis"]
        jenis_db[str(j["id_jenis"])] = j["id_jenis"]
    baris = titik_csv.baca_csv(file.file.read(titik_csv.MAKS_BYTE + 1), jenis_db)
    polsek = {r["i"]: r["id_polsek"] for r in conn.execute(
        """SELECT i, (SELECT p.id_polsek FROM polsek p WHERE p.geom IS NOT NULL
                       AND ST_Covers(p.geom, ST_SetSRID(ST_MakePoint(t.lng, t.lat), 4326)) ORDER BY p.id_polsek LIMIT 1) AS id_polsek
           FROM unnest(%s::float8[], %s::float8[]) WITH ORDINALITY AS t(lng, lat, i)""",
        ([b["lng"] for b in baris], [b["lat"] for b in baris])).fetchall()}
    tanpa = sum(1 for v in polsek.values() if v is None)
    if not dry_run:
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO titik_kejadian (id_polsek, id_jenis, tanggal, geom) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                [(polsek[i], b["id_jenis"], b["tanggal"], b["lng"], b["lat"]) for i, b in enumerate(baris, start=1)])
        audit.catat(conn, user, "impor", "titik", None, {"berkas": file.filename, "baris": len(baris), "tanpa_polsek": tanpa})
        conn.commit()
    return {"baris_dibaca": len(baris), "tersimpan": 0 if dry_run else len(baris), "tanpa_polsek": tanpa,
            "peringatan": [f"{tanpa} titik di luar semua wilayah Polsek (id_polsek = null; tetap tampil di heatmap)"] if tanpa else [],
            "disimpan": not dry_run}


@router.post("/titik", status_code=201, summary="Tambah satu titik kejadian (operator/admin)")
def tambah_titik(body: TitikBaru, conn: Conn, user: Pengguna):
    _cek_wilayah(body.lat, body.lng)
    _cek_referensi(conn, body.id_jenis, body.id_polsek)
    id_polsek = body.id_polsek if body.id_polsek is not None else _polsek_dari_titik(conn, body.lng, body.lat)
    id_titik = conn.execute(
        "INSERT INTO titik_kejadian (id_polsek, id_jenis, tanggal, geom) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) RETURNING id_titik",
        (id_polsek, body.id_jenis, body.tanggal, body.lng, body.lat)).fetchone()["id_titik"]
    row = _ambil(conn, id_titik)
    audit.catat(conn, user, "tambah", "titik", id_titik, row)
    conn.commit()
    return row


@router.put("/titik/{id_titik}", summary="Ubah titik kejadian - semua field boleh diubah (operator/admin)")
def ubah_titik(id_titik: int, body: TitikUbah, conn: Conn, user: Pengguna):
    kirim = body.model_dump(exclude_unset=True)
    if not kirim or (("lat" in kirim) != ("lng" in kirim)) or any(kirim.get(k, 0) is None for k in ("lat", "lng", "id_jenis", "tanggal")):
        raise validasi_gagal("Kirim minimal satu field; lat dan lng harus dikirim berpasangan (tidak boleh null)", ["lat", "lng"])
    lama = _ambil(conn, id_titik)
    if lama is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    baru = {k: kirim.get(k, lama[k]) for k in ("lat", "lng", "id_jenis", "tanggal")}
    _cek_wilayah(baru["lat"], baru["lng"])
    _cek_referensi(conn, kirim.get("id_jenis"), kirim.get("id_polsek"))
    if kirim.get("id_polsek") is not None:
        id_polsek = kirim["id_polsek"]
    elif "id_polsek" in kirim or "lat" in kirim:                     # null eksplisit atau lokasi pindah -> hitung ulang dari poligon
        id_polsek = _polsek_dari_titik(conn, baru["lng"], baru["lat"])
    else:
        id_polsek = lama["id_polsek"]
    conn.execute("""UPDATE titik_kejadian SET id_polsek = %s, id_jenis = %s, tanggal = %s,
                    geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326) WHERE id_titik = %s""",
                 (id_polsek, baru["id_jenis"], baru["tanggal"], baru["lng"], baru["lat"], id_titik))
    row = _ambil(conn, id_titik)
    audit.catat(conn, user, "ubah", "titik", id_titik, {"sebelum": lama, "sesudah": row})
    conn.commit()
    return row


@router.delete("/titik/{id_titik}", status_code=204, summary="Hapus titik kejadian (khusus admin)")
def hapus_titik(id_titik: int, conn: Conn, user: Admin):
    lama = _ambil(conn, id_titik)
    if lama is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    conn.execute("DELETE FROM titik_kejadian WHERE id_titik = %s", (id_titik,))
    audit.catat(conn, user, "hapus", "titik", id_titik, lama)
    conn.commit()
    return Response(status_code=204)
