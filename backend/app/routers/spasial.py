"""Query spasial PostGIS (GET publik): titik -> Polsek, Polsek terdekat/radius, Polsek di dalam kotak peta (bbox).
Koordinat selalu WGS 84: lat = lintang (-90..90), lng = bujur (-180..180). Jarak dalam meter (geography)."""
from fastapi import APIRouter, Query

from app.db import Conn
from app.errors import validasi_gagal
from app.params import daftar_zona
from app.services import rekap

router = APIRouter(prefix="/spasial", tags=["Spasial"])

_SQL = """
SELECT p.id_polsek, p.nama_polsek,
       COALESCE(z.total_kasus, 0) AS total_kasus,
       COALESCE(z.kategori_zona, hitung_kategori_zona(0)) AS kategori_zona,
       ST_Distance(p.geom::geography, pt.g::geography)::float8 AS jarak_meter,
       ST_Covers(p.geom, pt.g) AS di_dalam
FROM polsek p
CROSS JOIN (SELECT ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326) AS g) pt
LEFT JOIN zona_kerawanan z ON z.id_polsek = p.id_polsek AND z.tahun = %(tahun)s
WHERE p.geom IS NOT NULL {tambahan}
ORDER BY jarak_meter, p.id_polsek
LIMIT %(limit)s
"""


def _ringkas(r: dict) -> dict:
    return {"id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "total_kasus": r["total_kasus"],
            "kategori_zona": r["kategori_zona"], "jarak_meter": round(r["jarak_meter"], 1)}


@router.get("/titik", summary="Titik koordinat masuk wilayah Polsek mana?")
def titik(conn: Conn, lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180),
          tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru")):
    t = rekap.tentukan_tahun(conn, tahun)
    rows = conn.execute(_SQL.format(tambahan=""), {"lat": lat, "lng": lng, "tahun": t, "limit": 1}).fetchall()
    if not rows:
        return {"tahun": t, "titik": {"lat": lat, "lng": lng}, "di_dalam_wilayah": False, "polsek": None}
    r = rows[0]
    # di luar semua wilayah -> tetap kembalikan Polsek terdekat beserta jaraknya
    return {"tahun": t, "titik": {"lat": lat, "lng": lng}, "di_dalam_wilayah": bool(r["di_dalam"]), "polsek": _ringkas(r)}


@router.get("/terdekat", summary="Polsek terdekat dari sebuah titik (opsional dibatasi radius)")
def terdekat(conn: Conn, lat: float = Query(..., ge=-90, le=90), lng: float = Query(..., ge=-180, le=180),
             limit: int = Query(5, ge=1, le=30), radius_m: float | None = Query(None, gt=0, le=200_000, description="batas jarak (meter); kosong = tanpa batas"),
             tahun: int | None = Query(None, ge=2000, le=2100)):
    t = rekap.tentukan_tahun(conn, tahun)
    tambahan = "AND (%(radius)s::float8 IS NULL OR ST_DWithin(p.geom::geography, pt.g::geography, %(radius)s::float8))"
    rows = conn.execute(_SQL.format(tambahan=tambahan), {"lat": lat, "lng": lng, "tahun": t, "limit": limit, "radius": radius_m}).fetchall()
    return {"tahun": t, "titik": {"lat": lat, "lng": lng}, "radius_m": radius_m, "data": [_ringkas(r) for r in rows]}


@router.get("/bbox", summary="Polsek yang beririsan dengan kotak peta (GeoJSON)")
def dalam_bbox(conn: Conn,
               min_lng: float = Query(..., ge=-180, le=180), min_lat: float = Query(..., ge=-90, le=90),
               max_lng: float = Query(..., ge=-180, le=180), max_lat: float = Query(..., ge=-90, le=90),
               tahun: int | None = Query(None, ge=2000, le=2100), zona: str | None = Query(None, description="tinggi,sedang,rendah"),
               geometri: bool = Query(True, description="false = tanpa poligon (lebih ringan)")):
    if min_lng >= max_lng or min_lat >= max_lat:
        raise validasi_gagal("min_lng/min_lat harus lebih kecil dari max_lng/max_lat",
                             [n for n, ok in (("min_lng", min_lng < max_lng), ("min_lat", min_lat < max_lat)) if not ok])
    zona_l = daftar_zona(zona)
    t = rekap.tentukan_tahun(conn, tahun)
    ids = [r["id_polsek"] for r in conn.execute(
        "SELECT id_polsek FROM polsek WHERE geom && ST_MakeEnvelope(%(a)s, %(b)s, %(c)s, %(d)s, 4326) "
        "AND ST_Intersects(geom, ST_MakeEnvelope(%(a)s, %(b)s, %(c)s, %(d)s, 4326))",
        {"a": min_lng, "b": min_lat, "c": max_lng, "d": max_lat}).fetchall()]
    rows = rekap.rekap_per_polsek(conn, t, polsek=ids, zona=zona_l, dengan_geom=geometri)
    return {"type": "FeatureCollection", "features": rekap.fitur_geojson(rows, t)}
