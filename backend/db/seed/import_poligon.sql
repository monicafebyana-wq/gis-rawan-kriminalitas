-- import_poligon.sql
-- Impor poligon wilayah (GeoJSON) ke kolom polsek.geom + VALIDASI geometri.
-- Satu transaksi: kalau ada pengecekan gagal -> rollback, kolom geom tidak berubah.
-- Aman dijalankan berulang (geom ditimpa). Prasyarat: tabel polsek sudah terisi (jalankan import.sh dulu).
--
--   docker exec gis_kriminalitas_db sh /seed/import_poligon.sh [nama_berkas.geojson]
--
-- Format GeoJSON yang diharapkan: FeatureCollection, tiap feature punya
--   properties.id_polsek (1-27, sama dengan data/bersih/polsek.csv) dan properties.nama_polsek, geometri Polygon/MultiPolygon, WGS 84.
\set ON_ERROR_STOP on
\if :{?berkas}
\else
  \set berkas /data/geojson/polsek_poligon.geojson
\endif
\if :{?toleransi_overlap_km2}
\else
  \set toleransi_overlap_km2 0.05
\endif

\echo '== Impor poligon wilayah =='
\echo :berkas
\set geojson `cat :berkas`

BEGIN;

-- ---------- 1. baca GeoJSON ke tabel sementara ----------
CREATE TEMP TABLE stg_poligon ON COMMIT DROP AS
SELECT (f -> 'properties' ->> 'id_polsek')::INTEGER  AS id_polsek,
       f -> 'properties' ->> 'nama_polsek'           AS nama_geojson,
       GeometryType(g)                                AS tipe_asli,
       ST_IsValid(g)                                  AS valid_asli,
       g                                              AS geom_asli
FROM jsonb_array_elements(:'geojson'::jsonb -> 'features') AS f,
     LATERAL (SELECT ST_SetSRID(ST_GeomFromGeoJSON((f -> 'geometry')::TEXT), 4326) AS g) AS x;

-- ---------- 2. perbaiki geometri tidak valid (ST_MakeValid) + seragamkan ke MultiPolygon ----------
ALTER TABLE stg_poligon ADD COLUMN geom geometry(MultiPolygon, 4326);
UPDATE stg_poligon
SET geom = ST_Multi(ST_CollectionExtract(CASE WHEN valid_asli THEN geom_asli ELSE ST_MakeValid(geom_asli) END, 3));

-- ---------- 3. tulis ke tabel utama ----------
UPDATE polsek p SET geom = s.geom FROM stg_poligon s WHERE p.id_polsek = s.id_polsek;

-- ---------- 4. verifikasi ----------
CREATE TEMP TABLE cek (no SERIAL, pengecekan TEXT, diharapkan BIGINT, hasil BIGINT) ON COMMIT DROP;
INSERT INTO cek (pengecekan, diharapkan, hasil) VALUES
 ('Jumlah feature di GeoJSON', 27, (SELECT count(*) FROM stg_poligon)),
 ('id_polsek ganda di GeoJSON', 0, (SELECT count(*) - count(DISTINCT id_polsek) FROM stg_poligon)),
 ('id_polsek di GeoJSON yang tidak ada di tabel polsek', 0,
    (SELECT count(*) FROM stg_poligon s LEFT JOIN polsek p USING (id_polsek) WHERE p.id_polsek IS NULL)),
 ('Polsek di database yang TIDAK ada di GeoJSON ini', 0,
    (SELECT count(*) FROM polsek p LEFT JOIN stg_poligon s USING (id_polsek) WHERE s.id_polsek IS NULL)),
 ('Polsek yang geom-nya masih kosong setelah impor', 0,
    (SELECT count(*) FROM polsek WHERE geom IS NULL)),
 ('Nama Polsek di GeoJSON BEDA dari database (id/nama tertukar?)', 0,
    (SELECT count(*) FROM stg_poligon s JOIN polsek p USING (id_polsek) WHERE s.nama_geojson IS DISTINCT FROM p.nama_polsek)),
 ('Geometri kosong atau bukan Polygon/MultiPolygon', 0,
    (SELECT count(*) FROM stg_poligon WHERE ST_IsEmpty(geom) OR tipe_asli NOT IN ('POLYGON', 'MULTIPOLYGON'))),
 ('Geometri TIDAK valid setelah perbaikan', 0,
    (SELECT count(*) FROM polsek WHERE NOT ST_IsValid(geom))),
 ('Bukan MultiPolygon / SRID bukan 4326 di tabel polsek', 0,
    (SELECT count(*) FROM polsek WHERE NOT (GeometryType(geom) = 'MULTIPOLYGON' AND ST_SRID(geom) = 4326))),
 ('Di luar kotak Kab. Bandung (lon 107.2-108.2, lat -7.6 s/d -6.6): lon/lat tertukar atau CRS salah?', 0,
    (SELECT count(*) FROM polsek WHERE NOT (ST_XMin(geom) >= 107.2 AND ST_XMax(geom) <= 108.2
                                            AND ST_YMin(geom) >= -7.6 AND ST_YMax(geom) <= -6.6))),
 ('Luas poligon tidak wajar (< 1 km2 atau > 600 km2)', 0,
    (SELECT count(*) FROM polsek WHERE ST_Area(geom::geography) / 1e6 NOT BETWEEN 1 AND 600)),
 ('Pasangan poligon tumpang tindih > toleransi (km2)', 0,
    (SELECT count(*) FROM polsek a JOIN polsek b ON a.id_polsek < b.id_polsek AND a.geom && b.geom
      WHERE ST_Area(ST_Intersection(a.geom, b.geom)::geography) / 1e6 > :toleransi_overlap_km2));

SELECT pengecekan, diharapkan, hasil, CASE WHEN diharapkan = hasil THEN 'LULUS' ELSE 'GAGAL' END AS status FROM cek ORDER BY no;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM cek WHERE diharapkan IS DISTINCT FROM hasil) THEN
        RAISE EXCEPTION 'VERIFIKASI GAGAL - semua perubahan dibatalkan (rollback). Lihat tabel di atas.';
    END IF;
END $$;

-- informasi (bukan kegagalan)
\echo '-- Info: geometri yang diperbaiki otomatis (ST_MakeValid)'
SELECT id_polsek, nama_geojson FROM stg_poligon WHERE NOT valid_asli;

COMMIT;
ANALYZE polsek;
\echo '== Verifikasi LULUS, poligon tersimpan =='

\echo ''
\echo '-- Ringkasan'
SELECT count(*) AS polsek_ber_poligon,
       round(sum(ST_Area(geom::geography)) / 1e6) AS total_luas_km2,
       min(ST_NPoints(geom)) AS titik_min, max(ST_NPoints(geom)) AS titik_maks
FROM polsek;
\echo '-- 5 wilayah terluas'
SELECT nama_polsek, round(ST_Area(geom::geography) / 1e6) AS luas_km2 FROM polsek ORDER BY 2 DESC LIMIT 5;
\echo '-- Uji spasial: titik di Soreang (-7.0252, 107.5198) masuk wilayah mana?'
SELECT nama_polsek FROM polsek WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(107.5198, -7.0252), 4326));
