"""Buat atau ubah akun admin/operator (password disimpan sebagai hash bcrypt).

Jalankan dari folder backend/ (venv aktif, database menyala):
    python -m app.buat_pengguna admin --peran admin
    python -m app.buat_pengguna petugas1 --peran operator
Kalau username sudah ada, password dan peran-nya diperbarui.
"""
import argparse
import getpass
import re
import sys

import psycopg

from app import security
from app.db import conninfo


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("username")
    ap.add_argument("--peran", choices=["admin", "operator"], default="operator")
    ap.add_argument("--password", help="(tidak disarankan: terekam di riwayat terminal) kosongkan agar ditanya")
    a = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", a.username):
        print("Username 3-50 karakter: huruf, angka, titik, garis bawah, atau strip.")
        return 1
    pw = a.password
    if pw is None:
        pw = getpass.getpass("Password: ")
        if pw != getpass.getpass("Ulangi password: "):
            print("Password tidak sama.")
            return 1
    if len(pw) < 8 or len(pw.encode("utf-8")) > security.MAKS_BYTE_PASSWORD:
        print("Password minimal 8 karakter dan maksimal 72 byte.")
        return 1

    with psycopg.connect(conninfo()) as conn:
        baru = conn.execute(
            """INSERT INTO pengguna (username, password_hash, peran) VALUES (%s, %s, %s)
               ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, peran = EXCLUDED.peran
               RETURNING (xmax = 0) AS baru""", (a.username, security.hash_password(pw), a.peran)).fetchone()[0]
    print(f"Akun '{a.username}' ({a.peran}) {'dibuat' if baru else 'diperbarui'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
