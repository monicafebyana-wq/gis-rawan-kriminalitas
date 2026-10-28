"""Catat riwayat perubahan ke tabel audit_log. Dipanggil di dalam transaksi yang sama dengan perubahannya,
jadi kalau perubahan dibatalkan (rollback), catatannya ikut batal.

    from app.services import audit
    audit.catat(conn, user, "ubah", "kasus", id_kasus, {"sebelum": lama, "sesudah": baru})
Tipe non-JSON (tanggal, dll.) otomatis diubah jadi teks.
JANGAN pernah menaruh password/hash di `detail`.
"""
import json

import psycopg
from psycopg.types.json import Jsonb


def catat(conn: psycopg.Connection, user: dict, aksi: str, entitas: str, id_entitas=None, detail: dict | None = None) -> None:
    conn.execute(
        """INSERT INTO audit_log (id_pengguna, username, aksi, entitas, id_entitas, detail)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user["id_pengguna"], user["username"], aksi, entitas,
         None if id_entitas is None else str(id_entitas), None if detail is None else Jsonb(detail, dumps=lambda o: json.dumps(o, default=str))))
