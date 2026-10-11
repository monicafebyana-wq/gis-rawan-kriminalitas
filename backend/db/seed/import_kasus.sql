-- import_kasus.sql
-- Impor data bersih (data/bersih/*.csv) ke tabel polsek + kasus_kejahatan, hitung zona, lalu VERIFIKASI.
-- Semua dalam SATU transaksi: kalau ada pengecekan gagal, tidak ada yang tersimpan (rollback).
-- Aman dijalankan berulang (idempoten): data tahun yang sama diganti, bukan digandakan.
--
-- Dijalankan lewat:  docker exec gis_kriminalitas_db sh /seed/import.sh [total_diharapkan]
\set ON_ERROR_STOP on
\if :{?expect_total}
\else
  \set expect_total 1163
\endif

\echo '== Impor rekap kriminalitas =='
BEGIN;

-- ---------- 1. muat CSV ke tabel sementara ----------
CREATE TEMP TABLE stg_polsek (id_polsek INTEGER, nama_polsek TEXT, nama_wilayah_resmi TEXT) ON COMMIT DROP;
CREATE TEMP TABLE stg_kasus  (id_kasus INTEGER, id_polsek INTEGER, id_jenis INTEGER, tahun INTEGER, jumlah INTEGER) ON COMMIT DROP;
-- rekap lebar: c1=id_polsek, c2=nama, c3..c20=18 jenis, c21=Jumlah, c22=kategori_zona (dipakai untuk uji silang)
CREATE TEMP TABLE stg_rekap (c1 TEXT, c2 TEXT, c3 TEXT, c4 TEXT, c5 TEXT, c6 TEXT, c7 TEXT, c8 TEXT, c9 TEXT, c10 TEXT, c11 TEXT,
                             c12 TEXT, c13 TEXT, c14 TEXT, c15 TEXT, c16 TEXT, c17 TEXT, c18 TEXT, c19 TEXT, c20 TEXT, c21 TEXT, c22 TEXT) ON COMMIT DROP;

\copy stg_polsek FROM '/data/bersih/polsek.csv' CSV HEADER
\copy stg_kasus  FROM '/data/bersih/kasus_kejahatan.csv' CSV HEADER
\copy stg_rekap  FROM '/data/bersih/rekap_2024_bersih.csv' CSV HEADER

-- ---------- 2. validasi isi CSV sebelum menyentuh tabel utama ----------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM stg_kasus GROUP BY id_polsek, id_jenis, tahun HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'CSV berisi kombinasi polsek+jenis+tahun ganda';
    END IF;
    IF EXISTS (SELECT 1 FROM stg_kasus WHERE jumlah IS NULL OR jumlah < 0) THEN
        RAISE EXCEPTION 'CSV berisi jumlah kosong atau negatif';
    END IF;
    IF EXISTS (SELECT 1 FROM stg_kasus s LEFT JOIN jenis_kejahatan j USING (id_jenis) WHERE j.id_jenis IS NULL) THEN
        RAISE EXCEPTION 'id_jenis di CSV tidak ada di tabel jenis_kejahatan (sudah menjalankan migrasi 003?)';
    END IF;
    IF EXISTS (SELECT 1 FROM stg_kasus s LEFT JOIN stg_polsek p USING (id_polsek) WHERE p.id_polsek IS NULL) THEN
        RAISE EXCEPTION 'id_polsek di kasus_kejahatan.csv tidak ada di polsek.csv';
    END IF;
END $$;

-- ---------- 3. tulis ke tabel utama ----------
INSERT INTO polsek (id_polsek, nama_polsek, nama_wilayah_resmi)
SELECT id_polsek, nama_polsek, nama_wilayah_resmi FROM stg_polsek
ON CONFLICT (id_polsek) DO UPDATE
    SET nama_polsek = EXCLUDED.nama_polsek,
        nama_wilayah_resmi = EXCLUDED.nama_wilayah_resmi;     -- kolom geom tidak disentuh

DELETE FROM kasus_kejahatan WHERE tahun IN (SELECT DISTINCT tahun FROM stg_kasus);   -- mode "timpa" per tahun
INSERT INTO kasus_kejahatan (id_polsek, id_jenis, tahun, jumlah)
SELECT id_polsek, id_jenis, tahun, jumlah FROM stg_kasus ORDER BY id_polsek, id_jenis, tahun;

SELECT sinkronkan_urutan_id();      -- id polsek diisi eksplisit dari CSV
SELECT refresh_zona_kerawanan();    -- hitung ulang zona

-- ---------- 4. verifikasi ----------
CREATE TEMP TABLE cek (no SERIAL, pengecekan TEXT, diharapkan BIGINT, hasil BIGINT) ON COMMIT DROP;
INSERT INTO cek (pengecekan, diharapkan, hasil) VALUES
 ('Jumlah Polsek di tabel polsek', 27, (SELECT count(*) FROM polsek)),
 ('Jumlah jenis di tabel jenis_kejahatan', 18, (SELECT count(*) FROM jenis_kejahatan)),
 ('Baris kasus_kejahatan untuk tahun yang diimpor (27 x 18)', 486,
    (SELECT count(*) FROM kasus_kejahatan WHERE tahun IN (SELECT DISTINCT tahun FROM stg_kasus))),
 ('TOTAL kasus tahun yang diimpor', :expect_total,
    (SELECT COALESCE(sum(jumlah), 0)::BIGINT FROM kasus_kejahatan WHERE tahun IN (SELECT DISTINCT tahun FROM stg_kasus))),
 ('Polsek yang total kasusnya BEDA dari kolom Jumlah di rekap CSV', 0,
    (SELECT count(*) FROM stg_rekap r
       LEFT JOIN (SELECT id_polsek, sum(jumlah) AS s FROM kasus_kejahatan
                  WHERE tahun IN (SELECT DISTINCT tahun FROM stg_kasus) GROUP BY id_polsek) k ON k.id_polsek = r.c1::INTEGER
      WHERE k.s IS DISTINCT FROM r.c21::BIGINT)),
 ('Polsek yang kategori zonanya BEDA dari rekap CSV', 0,
    (SELECT count(*) FROM stg_rekap r
       LEFT JOIN zona_kerawanan z ON z.id_polsek = r.c1::INTEGER AND z.tahun IN (SELECT DISTINCT tahun FROM stg_kasus)
      WHERE z.kategori_zona IS DISTINCT FROM r.c22));

SELECT pengecekan, diharapkan, hasil, CASE WHEN diharapkan = hasil THEN 'LULUS' ELSE 'GAGAL' END AS status FROM cek ORDER BY no;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM cek WHERE diharapkan IS DISTINCT FROM hasil) THEN
        RAISE EXCEPTION 'VERIFIKASI GAGAL - semua perubahan dibatalkan (rollback). Lihat tabel di atas.';
    END IF;
END $$;

COMMIT;
\echo '== Verifikasi LULUS, data tersimpan =='

-- ---------- 5. info silang dengan slide (hanya tampilan) ----------
\echo ''
\echo '-- Distribusi zona'
SELECT kategori_zona, count(*) AS jumlah_polsek FROM zona_kerawanan
WHERE tahun IN (SELECT DISTINCT tahun FROM kasus_kejahatan) GROUP BY 1 ORDER BY 1;
\echo '-- 4 jenis terbanyak (slide: 235, 198, 154, 151 = 738 atau 63%)'
SELECT j.nama_jenis, sum(k.jumlah) AS jumlah FROM kasus_kejahatan k JOIN jenis_kejahatan j USING (id_jenis)
GROUP BY j.nama_jenis ORDER BY 2 DESC LIMIT 4;
\echo '-- Tertinggi & terendah (slide: Cicalengka 76, Nagreg 5)'
(SELECT nama_polsek, total_kasus FROM v_zona_polsek ORDER BY total_kasus DESC, id_polsek LIMIT 1)
UNION ALL
(SELECT nama_polsek, total_kasus FROM v_zona_polsek ORDER BY total_kasus ASC, id_polsek LIMIT 1);
