"""Zonasi kerawanan. ATURAN ambang (>=60 tinggi, 30-59 sedang, <30 rendah) hanya ada SATU tempat:
fungsi SQL hitung_kategori_zona() di backend/db/migrations/002_fungsi_zonasi.sql.
Modul ini hanya memanggilnya, supaya Python dan database tidak pernah berbeda hasil.

Pemakaian (di router/endpoint):
    from app.services import zonasi

    # setelah tambah/ubah/hapus kasus atau impor CSV:
    zonasi.refresh_zona(conn, tahun)          # atau tanpa tahun = semua tahun

    zona = zonasi.kategori_zona(conn, 61)     # -> "tinggi"
"""
import psycopg


def kategori_zona(conn: psycopg.Connection, total_kasus: int) -> str:
    """Klasifikasi satu angka total kasus (semua jenis) -> 'tinggi' | 'sedang' | 'rendah'."""
    return conn.execute("SELECT hitung_kategori_zona(%s) AS k", (total_kasus,)).fetchone()["k"]


def refresh_zona(conn: psycopg.Connection, tahun: int | None = None) -> int:
    """Hitung ulang tabel zona_kerawanan. tahun=None -> semua tahun yang punya data.
    Mengembalikan jumlah baris zona yang ditulis. PANGGIL setiap data kasus berubah.
    (Commit dilakukan oleh dependency `Conn` saat request selesai.)"""
    return conn.execute("SELECT refresh_zona_kerawanan(%s::smallint) AS n", (tahun,)).fetchone()["n"]


def ambil_zona(conn: psycopg.Connection, tahun: int) -> list[dict]:
    """Zona semua Polsek pada satu tahun, urut dari kasus terbanyak."""
    return conn.execute(
        "SELECT id_polsek, nama_polsek, tahun, total_kasus, kategori_zona FROM v_zona_polsek "
        "WHERE tahun = %s ORDER BY total_kasus DESC, id_polsek", (tahun,)
    ).fetchall()
