"""Titik kejadian (lat/lng per kejadian) untuk HEATMAP + berita yang melengkapinya.
Tabel terpisah dari rekap kasus -> tidak mengubah jumlah kasus / zona.

  GET    /api/heatmap                titik dirangkum per sel grid -> [{lat, lng, bobot}]            PUBLIK (koordinat persis tidak dibuka)
  GET    /api/titik/sebaran          titik per sel grid + rincian jenis kejahatan                    PUBLIK
  GET    /api/berita-kejadian        titik yang punya berita (GeoJSON, lengkap dengan tautan)       PUBLIK
  GET    /api/titik                  daftar titik persis (paginasi)                                  login
  POST   /api/titik                  tambah titik (boleh sekalian 1 berita)                          operator/admin
  POST   /api/titik/import           impor CSV (dry_run; kolom berita opsional)                      operator/admin
  PUT    /api/titik/{id}             ubah (semua field boleh)                                        operator/admin
  DELETE /api/titik/{id}             hapus (berita ikut terhapus)                                    khusus admin
  GET    /api/titik/{id}/berita      daftar berita satu titik                                        login
  POST   /api/titik/{id}/berita      tambah berita                                                   operator/admin
  PUT    /api/berita/{id}            ubah berita                                                     operator/admin
  DELETE /api/berita/{id}            hapus berita                                                    khusus admin
id_polsek diisi OTOMATIS dari poligon wilayah (NULL bila di luar semua wilayah), kecuali kolom `polsek`/`id_polsek` diisi eksplisit.
sumber_data: laporan | berita | simulasi.  akurasi: tepat | desa | kecamatan (perkiraan lokasi dari berita).
"""
from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, File, Form, Query, Response, UploadFile
from pydantic import BaseModel, Field

from app.db import Conn
from app.deps import Admin, Pengguna
from app.errors import ApiError, tidak_ditemukan, validasi_gagal
from app.params import daftar_int
from app.services import audit, titik_csv
from app.services.geojson_polsek import BATAS_WILAYAH
from app.services.impor_csv import normalkan_nama
from app.services.titik_csv import AKURASI_BOLEH, SUMBER_BOLEH, TGL_MAX, TGL_MIN

router = APIRouter(tags=["Titik kejadian"])
GRID_MIN = 0.0005                    # ~55 m: sel grid terkecil yang boleh diminta publik
POLA_URL = r"(?i)^https?://\S+$"     # hanya http/https; mencegah javascript: di tautan

_DARI = "titik_kejadian t LEFT JOIN polsek p ON p.id_polsek = t.id_polsek JOIN jenis_kejahatan j ON j.id_jenis = t.id_jenis"
_KOLOM = """t.id_titik, ST_Y(t.geom)::float8 AS lat, ST_X(t.geom)::float8 AS lng, t.id_polsek, p.nama_polsek,
            t.id_jenis, j.nama_jenis, t.tanggal, t.sumber_data, t.akurasi,
            (SELECT count(*) FROM berita_kejadian b WHERE b.id_titik = t.id_titik)::int AS jumlah_berita"""
_KOLOM_BERITA = "id_berita, id_titik, judul, sumber, url, tanggal_terbit, ringkasan"
_WHERE = """(%(tahun)s::int IS NULL OR (t.tanggal >= make_date(%(tahun)s::int, 1, 1) AND t.tanggal < make_date(%(tahun)s::int + 1, 1, 1)))
            AND (%(dari)s::date IS NULL OR t.tanggal >= %(dari)s::date)
            AND (%(sampai)s::date IS NULL OR t.tanggal <= %(sampai)s::date)
            AND (%(jenis)s::int[] IS NULL OR t.id_jenis = ANY(%(jenis)s::int[]))
            AND (%(polsek)s::int[] IS NULL OR t.id_polsek = ANY(%(polsek)s::int[]))
            AND (%(sumber)s::text[] IS NULL OR t.sumber_data = ANY(%(sumber)s::text[]))"""

Sumber = Literal["laporan", "berita", "simulasi"]
Akurasi = Literal["tepat", "desa", "kecamatan"]


class BeritaBaru(BaseModel):
    judul: str = Field(min_length=3, max_length=300, description="judul ringkas (tulis dengan kalimat sendiri)")
    sumber: str = Field(min_length=2, max_length=100, description="nama media, mis. ANTARA")
    url: str = Field(max_length=2000, pattern=POLA_URL, description="http:// atau https://")
    tanggal_terbit: date | None = Field(None, ge=TGL_MIN, le=TGL_MAX)
    ringkasan: str | None = Field(None, max_length=600, description="ringkasan singkat dengan kalimat sendiri (jangan menyalin teks berita)")


class BeritaUbah(BaseModel):
    judul: str | None = Field(None, min_length=3, max_length=300)
    sumber: str | None = Field(None, min_length=2, max_length=100)
    url: str | None = Field(None, max_length=2000, pattern=POLA_URL)
    tanggal_terbit: date | None = Field(None, ge=TGL_MIN, le=TGL_MAX)
    ringkasan: str | None = Field(None, max_length=600)


class TitikBaru(BaseModel):
    lat: float = Field(ge=-90, le=90, description="lintang, mis. -7.02")
    lng: float = Field(ge=-180, le=180, description="bujur, mis. 107.52")
    id_jenis: int
    tanggal: date = Field(ge=TGL_MIN, le=TGL_MAX)
    id_polsek: int | None = Field(None, description="kosong = otomatis dari poligon wilayah")
    sumber: Sumber = "laporan"
    akurasi: Akurasi = "tepat"
    berita: BeritaBaru | None = None


class TitikUbah(BaseModel):
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    id_jenis: int | None = None
    tanggal: date | None = Field(None, ge=TGL_MIN, le=TGL_MAX)
    id_polsek: int | None = Field(None, description="kirim null = hitung ulang otomatis dari lokasi")
    sumber: Sumber | None = None
    akurasi: Akurasi | None = None


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


def _daftar_sumber(sumber: str | None) -> list[str] | None:
    if not sumber:
        return None
    nilai = [s.strip().lower() for s in sumber.split(",") if s.strip()]
    if not nilai or any(s not in SUMBER_BOLEH for s in nilai):
        raise validasi_gagal(f"Parameter sumber harus berisi: {', '.join(SUMBER_BOLEH)} (dipisah koma)", ["sumber"])
    return nilai


def _filter(tahun, dari, sampai, jenis, polsek, sumber=None) -> dict:
    return {"tahun": tahun, "dari": dari, "sampai": sampai, "jenis": daftar_int(jenis, "jenis"),
            "polsek": daftar_int(polsek, "polsek"), "sumber": _daftar_sumber(sumber)}


def _per_sumber(conn, prm: dict) -> dict:
    """Jumlah titik per sumber_data untuk filter yang sama: {"laporan": n, "berita": n, "simulasi": n}.
    Dipakai front end untuk memperingatkan bahwa sebagian titik adalah data simulasi."""
    hasil = {s: 0 for s in SUMBER_BOLEH}
    for r in conn.execute(f"SELECT t.sumber_data, count(*)::int AS n FROM titik_kejadian t WHERE {_WHERE} GROUP BY t.sumber_data", prm).fetchall():
        hasil[r["sumber_data"]] = r["n"]
    return hasil


def _simpan_berita(conn, id_titik: int, b: dict) -> dict | None:
    """None bila (id_titik, url) sudah ada."""
    return conn.execute(
        f"""INSERT INTO berita_kejadian (id_titik, judul, sumber, url, tanggal_terbit, ringkasan)
            VALUES (%(id)s, %(judul)s, %(sumber)s, %(url)s, %(tanggal_terbit)s, %(ringkasan)s)
            ON CONFLICT (id_titik, url) DO NOTHING RETURNING {_KOLOM_BERITA}""",
        {"id": id_titik, "judul": b["judul"], "sumber": b["sumber"], "url": b["url"],
         "tanggal_terbit": b.get("tanggal_terbit"), "ringkasan": b.get("ringkasan")}).fetchone()


# ---------------------------------------------------------------- heatmap & berita (publik)
@router.get("/heatmap", summary="Data heatmap: titik kejadian dirangkum per sel grid")
def heatmap(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="kosong = semua tahun"),
    dari: date | None = Query(None, description="YYYY-MM-DD"),
    sampai: date | None = Query(None, description="YYYY-MM-DD"),
    jenis: str | None = Query(None, description="id jenis dipisah koma"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
    sumber: str | None = Query(None, description="laporan,berita,simulasi (dipisah koma); kosong = semua"),
    grid: float = Query(0.002, ge=GRID_MIN, le=0.1, description="ukuran sel dalam derajat (0.001 ~ 110 m). Titik dalam satu sel dijumlahkan jadi `bobot`"),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek, sumber), "grid": grid}
    rows = conn.execute(
        f"""SELECT ST_Y(s)::float8 AS lat, ST_X(s)::float8 AS lng, count(*)::int AS bobot
            FROM (SELECT ST_SnapToGrid(t.geom, %(grid)s::float8) AS s FROM titik_kejadian t WHERE {_WHERE}) q
            GROUP BY s ORDER BY bobot DESC, lat, lng""", prm).fetchall()
    data = [{"lat": round(r["lat"], 6), "lng": round(r["lng"], 6), "bobot": r["bobot"]} for r in rows]
    return {"grid_derajat": grid, "total_titik": sum(d["bobot"] for d in data), "maks_bobot": data[0]["bobot"] if data else 0,
            "per_sumber": _per_sumber(conn, prm), "data": data}


@router.get("/titik/sebaran", summary="Titik kejadian per sel grid + rincian jenis kejahatan (publik)")
def sebaran_titik(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100),
    dari: date | None = Query(None),
    sampai: date | None = Query(None),
    jenis: str | None = Query(None),
    polsek: str | None = Query(None),
    sumber: str | None = Query(None, description="laporan,berita,simulasi (dipisah koma); kosong = semua"),
    grid: float = Query(GRID_MIN, ge=GRID_MIN, le=0.1),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek, sumber), "grid": grid}
    rows = conn.execute(
        f"""SELECT ST_Y(s)::float8 AS lat, ST_X(s)::float8 AS lng, nama_jenis, count(*)::int AS jumlah
            FROM (SELECT ST_SnapToGrid(t.geom, %(grid)s::float8) AS s, j.nama_jenis
                  FROM titik_kejadian t JOIN jenis_kejahatan j ON j.id_jenis = t.id_jenis
                  WHERE {_WHERE}) q
            GROUP BY s, nama_jenis""", prm).fetchall()
    sel: dict[tuple[float, float], list[dict]] = {}
    for r in rows:
        sel.setdefault((round(r["lat"], 6), round(r["lng"], 6)), []).append(
            {"nama_jenis": r["nama_jenis"], "jumlah": r["jumlah"]})
    data = [
        {"lat": k[0], "lng": k[1], "bobot": sum(x["jumlah"] for x in v),
         "rincian": sorted(v, key=lambda x: -x["jumlah"])}
        for k, v in sel.items()
    ]
    return {"grid_derajat": grid, "total_titik": sum(d["bobot"] for d in data), "per_sumber": _per_sumber(conn, prm), "data": data}


@router.get("/berita-kejadian", summary="Titik kejadian yang dilengkapi berita (GeoJSON, publik)")
def berita_kejadian(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="kosong = semua tahun"),
    dari: date | None = Query(None), sampai: date | None = Query(None),
    jenis: str | None = Query(None, description="id jenis dipisah koma"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
    limit: int = Query(500, ge=1, le=2000),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek), "limit": limit}
    rows = conn.execute(
        f"""SELECT {_KOLOM},
                   (SELECT jsonb_agg(jsonb_build_object('id_berita', b.id_berita, 'judul', b.judul, 'sumber', b.sumber, 'url', b.url,
                                                        'tanggal_terbit', b.tanggal_terbit, 'ringkasan', b.ringkasan)
                                     ORDER BY b.tanggal_terbit DESC NULLS LAST, b.id_berita)
                    FROM berita_kejadian b WHERE b.id_titik = t.id_titik) AS berita
            FROM {_DARI}
            WHERE EXISTS (SELECT 1 FROM berita_kejadian b WHERE b.id_titik = t.id_titik) AND {_WHERE}
            ORDER BY t.tanggal DESC, t.id_titik DESC LIMIT %(limit)s""", prm).fetchall()
    fitur = [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lng"], r["lat"]]},
        "properties": {"id_titik": r["id_titik"], "tanggal": r["tanggal"].isoformat(), "id_jenis": r["id_jenis"], "nama_jenis": r["nama_jenis"],
                       "id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "sumber_data": r["sumber_data"],
                       "akurasi": r["akurasi"], "berita": r["berita"] or []},
    } for r in rows]
    return {"type": "FeatureCollection", "total": len(fitur), "features": fitur}


# ---------------------------------------------------------------- titik persis (login)
@router.get("/titik", summary="Daftar titik kejadian persis (operator/admin)")
def daftar_titik(
    conn: Conn, user: Pengguna,
    tahun: int | None = Query(None, ge=2000, le=2100), dari: date | None = Query(None), sampai: date | None = Query(None),
    jenis: str | None = Query(None), polsek: str | None = Query(None),
    sumber: str | None = Query(None, description="laporan,berita,simulasi (dipisah koma)"),
    ada_berita: bool | None = Query(None, description="true = hanya titik yang punya berita; false = yang belum"),
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=500),
):
    prm = {**_filter(tahun, dari, sampai, jenis, polsek, sumber), "ada_berita": ada_berita, "limit": limit, "offset": (page - 1) * limit}
    syarat = _WHERE + " AND (%(ada_berita)s::bool IS NULL OR EXISTS (SELECT 1 FROM berita_kejadian b WHERE b.id_titik = t.id_titik) = %(ada_berita)s::bool)"
    total = conn.execute(f"SELECT count(*) AS n FROM titik_kejadian t WHERE {syarat}", prm).fetchone()["n"]
    data = conn.execute(f"SELECT {_KOLOM} FROM {_DARI} WHERE {syarat} ORDER BY t.id_titik DESC LIMIT %(limit)s OFFSET %(offset)s", prm).fetchall()
    return {"page": page, "limit": limit, "total_data": total, "data": data}


@router.post("/titik/import", summary="Impor titik kejadian dari CSV (operator/admin)")
def impor_titik(
    conn: Conn, user: Pengguna,
    file: UploadFile = File(..., description="CSV dengan kolom lat, lng, jenis, tanggal (+ opsional: sumber, akurasi, polsek, judul_berita, sumber_berita, url_berita, tanggal_berita, ringkasan)"),
    dry_run: bool = Form(False, description="true = hanya validasi, tidak menyimpan"),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise validasi_gagal("Berkas harus berekstensi .csv", ["file"])
    jenis_db: dict[str, int] = {}
    for j in conn.execute("SELECT id_jenis, kode_jenis, nama_jenis FROM jenis_kejahatan").fetchall():
        jenis_db[j["kode_jenis"].upper()] = jenis_db[j["nama_jenis"].lower()] = j["id_jenis"]
        jenis_db[str(j["id_jenis"])] = j["id_jenis"]
    polsek_db = {p["nama_polsek"].lower(): p["id_polsek"] for p in conn.execute("SELECT id_polsek, nama_polsek FROM polsek").fetchall()}
    baris = titik_csv.baca_csv(file.file.read(titik_csv.MAKS_BYTE + 1), jenis_db, polsek_db)
    otomatis = {r["i"]: r["id_polsek"] for r in conn.execute(
        """SELECT i, (SELECT p.id_polsek FROM polsek p WHERE p.geom IS NOT NULL
                       AND ST_Covers(p.geom, ST_SetSRID(ST_MakePoint(t.lng, t.lat), 4326)) ORDER BY p.id_polsek LIMIT 1) AS id_polsek
           FROM unnest(%s::float8[], %s::float8[]) WITH ORDINALITY AS t(lng, lat, i)""",
        ([b["lng"] for b in baris], [b["lat"] for b in baris])).fetchall()}
    final = [b["id_polsek"] if b["id_polsek"] is not None else otomatis[i] for i, b in enumerate(baris, start=1)]
    tanpa = sum(1 for v in final if v is None)
    jumlah_berita = sum(1 for b in baris if b["berita"])
    per_sumber = {s: sum(1 for b in baris if b["sumber"] == s) for s in SUMBER_BOLEH}
    if not dry_run:
        sql = ("INSERT INTO titik_kejadian (id_polsek, id_jenis, tanggal, geom, sumber_data, akurasi) "
               "VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)")
        polos, dengan_berita = [], []
        for i, b in enumerate(baris):
            p = (final[i], b["id_jenis"], b["tanggal"], b["lng"], b["lat"], b["sumber"], b["akurasi"])
            (dengan_berita if b["berita"] else polos).append((p, b["berita"]))
        with conn.cursor() as cur:
            cur.executemany(sql, [p for p, _ in polos])
        for p, berita in dengan_berita:
            id_titik = conn.execute(sql + " RETURNING id_titik", p).fetchone()["id_titik"]
            _simpan_berita(conn, id_titik, berita)
        audit.catat(conn, user, "impor", "titik", None, {"berkas": file.filename, "baris": len(baris), "tanpa_polsek": tanpa,
                                                         "dengan_berita": jumlah_berita, "per_sumber": per_sumber})
        conn.commit()
    peringatan = [f"{tanpa} titik di luar semua wilayah Polsek (id_polsek = null; tetap tampil di heatmap)"] if tanpa else []
    if per_sumber["simulasi"]:
        peringatan.append(f"{per_sumber['simulasi']} titik bersumber 'simulasi' (data contoh, bukan data resmi)")
    return {"baris_dibaca": len(baris), "tersimpan": 0 if dry_run else len(baris), "tanpa_polsek": tanpa,
            "dengan_berita": jumlah_berita, "per_sumber": per_sumber, "peringatan": peringatan, "disimpan": not dry_run}


@router.post("/titik", status_code=201, summary="Tambah satu titik kejadian (operator/admin)")
def tambah_titik(body: TitikBaru, conn: Conn, user: Pengguna):
    _cek_wilayah(body.lat, body.lng)
    _cek_referensi(conn, body.id_jenis, body.id_polsek)
    if body.sumber == "berita" and body.berita is None:
        raise validasi_gagal("Titik bersumber 'berita' wajib menyertakan berita", ["berita"])
    id_polsek = body.id_polsek if body.id_polsek is not None else _polsek_dari_titik(conn, body.lng, body.lat)
    id_titik = conn.execute(
        """INSERT INTO titik_kejadian (id_polsek, id_jenis, tanggal, geom, sumber_data, akurasi)
           VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s) RETURNING id_titik""",
        (id_polsek, body.id_jenis, body.tanggal, body.lng, body.lat, body.sumber, body.akurasi)).fetchone()["id_titik"]
    if body.berita:
        _simpan_berita(conn, id_titik, body.berita.model_dump())
    row = _ambil(conn, id_titik)
    audit.catat(conn, user, "tambah", "titik", id_titik, row)
    conn.commit()
    return row


@router.put("/titik/{id_titik}", summary="Ubah titik kejadian - semua field boleh diubah (operator/admin)")
def ubah_titik(id_titik: int, body: TitikUbah, conn: Conn, user: Pengguna):
    kirim = body.model_dump(exclude_unset=True)
    if not kirim or (("lat" in kirim) != ("lng" in kirim)) or any(kirim.get(k, 0) is None for k in ("lat", "lng", "id_jenis", "tanggal", "sumber", "akurasi")):
        raise validasi_gagal("Kirim minimal satu field; lat dan lng harus dikirim berpasangan (tidak boleh null)", ["lat", "lng"])
    lama = _ambil(conn, id_titik)
    if lama is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    baru = {k: kirim.get(k, lama[k]) for k in ("lat", "lng", "id_jenis", "tanggal", "sumber_data", "akurasi")}
    if "sumber" in kirim:
        baru["sumber_data"] = kirim["sumber"]
    _cek_wilayah(baru["lat"], baru["lng"])
    _cek_referensi(conn, kirim.get("id_jenis"), kirim.get("id_polsek"))
    if kirim.get("id_polsek") is not None:
        id_polsek = kirim["id_polsek"]
    elif "id_polsek" in kirim or "lat" in kirim:                     # null eksplisit atau lokasi pindah -> hitung ulang dari poligon
        id_polsek = _polsek_dari_titik(conn, baru["lng"], baru["lat"])
    else:
        id_polsek = lama["id_polsek"]
    conn.execute("""UPDATE titik_kejadian SET id_polsek = %s, id_jenis = %s, tanggal = %s, sumber_data = %s, akurasi = %s,
                    geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326) WHERE id_titik = %s""",
                 (id_polsek, baru["id_jenis"], baru["tanggal"], baru["sumber_data"], baru["akurasi"], baru["lng"], baru["lat"], id_titik))
    row = _ambil(conn, id_titik)
    audit.catat(conn, user, "ubah", "titik", id_titik, {"sebelum": lama, "sesudah": row})
    conn.commit()
    return row


@router.delete("/titik/{id_titik}", status_code=204, summary="Hapus titik kejadian (khusus admin)")
def hapus_titik(id_titik: int, conn: Conn, user: Admin):
    lama = _ambil(conn, id_titik)
    if lama is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    conn.execute("DELETE FROM titik_kejadian WHERE id_titik = %s", (id_titik,))     # berita ikut terhapus (ON DELETE CASCADE)
    audit.catat(conn, user, "hapus", "titik", id_titik, lama)
    conn.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- berita per titik
@router.get("/titik/{id_titik}/berita", summary="Daftar berita satu titik (operator/admin)")
def daftar_berita(id_titik: int, conn: Conn, user: Pengguna):
    if conn.execute("SELECT 1 FROM titik_kejadian WHERE id_titik = %s", (id_titik,)).fetchone() is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    return {"data": conn.execute(f"SELECT {_KOLOM_BERITA} FROM berita_kejadian WHERE id_titik = %s ORDER BY tanggal_terbit DESC NULLS LAST, id_berita",
                                 (id_titik,)).fetchall()}


@router.post("/titik/{id_titik}/berita", status_code=201, summary="Tambah berita ke titik (operator/admin)")
def tambah_berita(id_titik: int, body: BeritaBaru, conn: Conn, user: Pengguna):
    if conn.execute("SELECT 1 FROM titik_kejadian WHERE id_titik = %s", (id_titik,)).fetchone() is None:
        raise tidak_ditemukan(f"Titik dengan id {id_titik} tidak ditemukan")
    row = _simpan_berita(conn, id_titik, body.model_dump())
    if row is None:
        raise ApiError(409, "DATA_SUDAH_ADA", "Berita dengan URL yang sama sudah ada pada titik ini")
    audit.catat(conn, user, "tambah", "berita", row["id_berita"], row)
    conn.commit()
    return row


@router.put("/berita/{id_berita}", summary="Ubah berita (operator/admin)")
def ubah_berita(id_berita: int, body: BeritaUbah, conn: Conn, user: Pengguna):
    kirim = body.model_dump(exclude_unset=True)
    if not kirim or any(kirim.get(k, 0) is None for k in ("judul", "sumber", "url")):
        raise validasi_gagal("Kirim minimal satu field (judul, sumber, dan url tidak boleh null)", ["judul", "sumber", "url", "tanggal_terbit", "ringkasan"])
    lama = conn.execute(f"SELECT {_KOLOM_BERITA} FROM berita_kejadian WHERE id_berita = %s FOR UPDATE", (id_berita,)).fetchone()
    if lama is None:
        raise tidak_ditemukan(f"Berita dengan id {id_berita} tidak ditemukan")
    set_sql = ", ".join(f"{k} = %({k})s" for k in kirim)          # nama kolom dari model (tetap); nilai lewat parameter
    try:
        row = conn.execute(f"UPDATE berita_kejadian SET {set_sql} WHERE id_berita = %(id)s RETURNING {_KOLOM_BERITA}", {**kirim, "id": id_berita}).fetchone()
    except psycopg.errors.UniqueViolation:
        raise ApiError(409, "DATA_SUDAH_ADA", "Titik ini sudah punya berita dengan URL tersebut")
    audit.catat(conn, user, "ubah", "berita", id_berita, {"sebelum": lama, "sesudah": row})
    conn.commit()
    return row


@router.delete("/berita/{id_berita}", status_code=204, summary="Hapus berita (khusus admin)")
def hapus_berita(id_berita: int, conn: Conn, user: Admin):
    row = conn.execute(f"DELETE FROM berita_kejadian WHERE id_berita = %s RETURNING {_KOLOM_BERITA}", (id_berita,)).fetchone()
    if row is None:
        raise tidak_ditemukan(f"Berita dengan id {id_berita} tidak ditemukan")
    audit.catat(conn, user, "hapus", "berita", id_berita, row)
    conn.commit()
    return Response(status_code=204)
