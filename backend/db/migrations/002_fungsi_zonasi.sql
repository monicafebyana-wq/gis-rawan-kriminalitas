-- 002_fungsi_zonasi.sql
-- Aturan zonasi di sisi database: satu sumber kebenaran untuk ambang 60 / 30.

-- Klasifikasi dari total kasus (semua jenis) satu Polsek pada satu tahun
CREATE FUNCTION hitung_kategori_zona(total INTEGER)
RETURNS VARCHAR(10)
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN total >= 60 THEN 'tinggi'
        WHEN total >= 30 THEN 'sedang'
        ELSE 'rendah'
    END
$$;

-- Hitung ulang tabel zona_kerawanan.
--   refresh_zona_kerawanan(2024)  -> hanya tahun 2024
--   refresh_zona_kerawanan()      -> semua tahun yang punya data kasus
-- Setiap Polsek selalu punya baris (total 0 jika tidak ada kasus). Mengembalikan jumlah baris yang ditulis.
-- PANGGIL setelah impor CSV / tambah / ubah / hapus kasus.
CREATE FUNCTION refresh_zona_kerawanan(p_tahun SMALLINT DEFAULT NULL)
RETURNS INTEGER
LANGUAGE plpgsql AS $$
DECLARE
    n INTEGER;
BEGIN
    -- buang zona untuk tahun yang sudah tidak punya data kasus sama sekali
    DELETE FROM zona_kerawanan z
    WHERE (p_tahun IS NULL OR z.tahun = p_tahun)
      AND NOT EXISTS (SELECT 1 FROM kasus_kejahatan k WHERE k.tahun = z.tahun);

    INSERT INTO zona_kerawanan (id_polsek, tahun, total_kasus, kategori_zona)
    SELECT p.id_polsek,
           t.tahun,
           COALESCE(SUM(k.jumlah), 0)::INTEGER,
           hitung_kategori_zona(COALESCE(SUM(k.jumlah), 0)::INTEGER)
    FROM polsek p
    CROSS JOIN (SELECT DISTINCT tahun FROM kasus_kejahatan
                WHERE p_tahun IS NULL OR tahun = p_tahun) t
    LEFT JOIN kasus_kejahatan k ON k.id_polsek = p.id_polsek AND k.tahun = t.tahun
    GROUP BY p.id_polsek, t.tahun
    ON CONFLICT (id_polsek, tahun) DO UPDATE
        SET total_kasus   = EXCLUDED.total_kasus,
            kategori_zona = EXCLUDED.kategori_zona;

    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$$;

-- Tampilan praktis untuk API/pengecekan: zona + nama Polsek
CREATE VIEW v_zona_polsek AS
SELECT z.tahun, p.id_polsek, p.nama_polsek, z.total_kasus, z.kategori_zona
FROM zona_kerawanan z
JOIN polsek p USING (id_polsek);

-- Setelah impor dengan id eksplisit (id dari CSV), sinkronkan penghitung id otomatis
-- supaya INSERT berikutnya (tanpa id) tidak bentrok. Panggil sekali di akhir skrip impor.
CREATE FUNCTION sinkronkan_urutan_id()
RETURNS VOID
LANGUAGE plpgsql AS $$
DECLARE
    t TEXT; kolom TEXT;
BEGIN
    FOR t, kolom IN VALUES ('polsek','id_polsek'), ('jenis_kejahatan','id_jenis'),
                           ('kasus_kejahatan','id_kasus'), ('zona_kerawanan','id_zona')
    LOOP
        EXECUTE format(
            'SELECT setval(pg_get_serial_sequence(%L, %L), COALESCE((SELECT MAX(%I) FROM %I), 0) + 1, false)',
            t, kolom, kolom, t);
    END LOOP;
END
$$;
