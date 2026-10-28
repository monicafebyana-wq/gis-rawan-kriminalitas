"""Query rekap yang dipakai bersama oleh /polsek, /statistik, dst.
Semua nilai dikirim sebagai parameter (%(nama)s) - jangan menyusun SQL dengan f-string."""
import psycopg

from app.errors import tidak_ditemukan


def tahun_terbaru(conn: psycopg.Connection) -> int | None:
    return conn.execute("SELECT max(tahun) AS t FROM kasus_kejahatan").fetchone()["t"]


def tentukan_tahun(conn: psycopg.Connection, tahun: int | None) -> int:
    """Tahun yang dipakai endpoint rekap: default = terbaru. 404 bila belum ada data / tahun itu tidak ada datanya."""
    if tahun is None:
        t = tahun_terbaru(conn)
        if t is None:
            raise tidak_ditemukan("Belum ada data kasus di database. Jalankan impor data (lihat README).")
        return t
    if conn.execute("SELECT 1 FROM kasus_kejahatan WHERE tahun = %s LIMIT 1", (tahun,)).fetchone() is None:
        raise tidak_ditemukan(f"Tidak ada data kasus untuk tahun {tahun}")
    return tahun


_SQL_REKAP = """
WITH tot AS (
    SELECT id_polsek,
           SUM(jumlah)::int AS total_semua,
           COALESCE(SUM(jumlah) FILTER (WHERE %(jenis)s::int[] IS NULL OR id_jenis = ANY(%(jenis)s::int[])), 0)::int AS total_filter
    FROM kasus_kejahatan
    WHERE tahun = %(tahun)s
    GROUP BY id_polsek
), dasar AS (
    SELECT p.id_polsek, p.nama_polsek, p.geom,
           COALESCE(t.total_filter, 0) AS total_kasus,
           COALESCE(t.total_semua, 0)  AS total_semua_jenis,
           -- kategori dari tabel zona_kerawanan; kalau barisnya belum ada, hitung langsung dari total
           COALESCE(z.kategori_zona, hitung_kategori_zona(COALESCE(t.total_semua, 0))) AS kategori_zona
    FROM polsek p
    LEFT JOIN tot t USING (id_polsek)
    LEFT JOIN zona_kerawanan z ON z.id_polsek = p.id_polsek AND z.tahun = %(tahun)s
)
SELECT id_polsek, nama_polsek, total_kasus, total_semua_jenis, kategori_zona
       {kolom_geom}
FROM dasar
WHERE (%(polsek)s::int[] IS NULL OR id_polsek = ANY(%(polsek)s::int[]))
  AND (%(zona)s::text[] IS NULL OR kategori_zona = ANY(%(zona)s::text[]))
ORDER BY {urut}
"""

_KOLOM_GEOM = """,
       ST_AsGeoJSON(geom, 6)::jsonb                 AS geometri,
       ST_Y(ST_PointOnSurface(geom))::float8        AS pusat_lat,
       ST_X(ST_PointOnSurface(geom))::float8        AS pusat_lng"""


def rekap_per_polsek(conn: psycopg.Connection, tahun: int, jenis: list[int] | None = None,
                     polsek: list[int] | None = None, zona: list[str] | None = None,
                     dengan_geom: bool = False, urut_kasus: bool = False) -> list[dict]:
    """Satu baris per Polsek: total_kasus (mengikuti filter jenis), total_semua_jenis, kategori_zona.
    kategori_zona SELALU dari total semua jenis (lihat api-contract.md)."""
    sql = _SQL_REKAP.format(kolom_geom=_KOLOM_GEOM if dengan_geom else "",
                            urut="total_semua_jenis DESC, id_polsek" if urut_kasus else "id_polsek")
    return conn.execute(sql, {"tahun": tahun, "jenis": jenis, "polsek": polsek, "zona": zona}).fetchall()


def fitur_geojson(rows: list[dict], tahun: int) -> list[dict]:
    """Baris rekap_per_polsek -> daftar Feature GeoJSON (dipakai /polsek dan /spasial/bbox)."""
    return [{
        "type": "Feature",
        "geometry": r.get("geometri"),          # None bila poligon belum diimpor / tidak diminta
        "properties": {
            "id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "tahun": tahun,
            "total_kasus": r["total_kasus"], "total_semua_jenis": r["total_semua_jenis"],
            "kategori_zona": r["kategori_zona"],
            "pusat": None if r.get("pusat_lat") is None else {"lat": round(r["pusat_lat"], 5), "lng": round(r["pusat_lng"], 5)},
        },
    } for r in rows]
