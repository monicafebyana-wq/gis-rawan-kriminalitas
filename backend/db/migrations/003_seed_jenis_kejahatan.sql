-- 003_seed_jenis_kejahatan.sql
-- Data referensi: 18 jenis kejahatan (id mengikuti urutan kolom di rekap CSV; sama dengan data/bersih/jenis_kejahatan.csv
-- dan docs/api-contract.md). Aman dijalankan ulang (upsert).

INSERT INTO jenis_kejahatan (id_jenis, kode_jenis, nama_jenis) VALUES
    (1, 'ANIAYA', 'Penganiayaan'),
    (2, 'ANIAYA_BERAT', 'Penganiayaan Berat'),
    (3, 'CURAS', 'Pencurian dengan Kekerasan (Curas)'),
    (4, 'CURAT', 'Pencurian dengan Pemberatan (Curat)'),
    (5, 'CURANMOR_R4', 'Curanmor Roda 4'),
    (6, 'CURANMOR_R2', 'Curanmor Roda 2'),
    (7, 'PERKOSAAN', 'Perkosaan'),
    (8, 'JUDI', 'Perjudian'),
    (9, 'RUSAK', 'Perusakan'),
    (10, 'TIPU', 'Penipuan'),
    (11, 'GELAP', 'Penggelapan'),
    (12, 'CURI_BIASA', 'Pencurian Biasa'),
    (13, 'KDRT', 'KDRT'),
    (14, 'SAJAM', 'Senjata Tajam'),
    (15, 'TDK_SENANG', 'Perbuatan Tidak Menyenangkan'),
    (16, 'KEROYOK', 'Pengeroyokan'),
    (17, 'CABUL', 'Pencabulan'),
    (18, 'LAIN2', 'Lain-lain')
ON CONFLICT (id_jenis) DO UPDATE
    SET kode_jenis = EXCLUDED.kode_jenis,
        nama_jenis = EXCLUDED.nama_jenis;

-- id dipakai eksplisit -> sinkronkan penghitung id otomatis
SELECT sinkronkan_urutan_id();
