"""Impor CSV (operator/admin; sudah jalan) & ekspor laporan (TODO No 33). Lihat api-contract.md bagian 2.8 & 3.5."""
from typing import Literal

from fastapi import APIRouter, File, Form, UploadFile

from app.db import Conn
from app.deps import Pengguna
from app.errors import belum_diimplementasi, validasi_gagal
from app.services import impor_csv as impor_csv_svc, zonasi

router = APIRouter(tags=["Laporan"])


@router.post("/import/csv", summary="Impor rekap CSV (operator/admin)")
def impor_csv(
    conn: Conn,
    user: Pengguna,
    file: UploadFile = File(..., description="CSV rekap (format data/rekap_kriminalitas_2024.csv)"),
    tahun: int = Form(..., ge=2000, le=2100),
    mode: Literal["timpa", "tambah"] = Form("timpa", description="timpa = hapus data tahun itu dulu; tambah = gabung/perbarui"),
    dry_run: bool = Form(False, description="true = hanya validasi, tidak menyimpan"),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise validasi_gagal("Berkas harus berekstensi .csv", ["file"])
    isi = file.file.read(impor_csv_svc.MAKS_BYTE + 1)
    polsek_db = {r["nama_polsek"].lower(): r["id_polsek"] for r in conn.execute("SELECT id_polsek, nama_polsek FROM polsek").fetchall()}
    baris, peringatan = impor_csv_svc.baca_csv(isi, polsek_db)            # error -> 400 dengan nomor baris
    if mode == "timpa" and peringatan:
        peringatan.append(f"Mode 'timpa': data tahun {tahun} untuk Polsek yang tidak ada di berkas ikut terhapus")
    total = sum(sum(b["jumlah"].values()) for b in baris)
    if not dry_run:
        impor_csv_svc.simpan(conn, tahun, baris, mode)
        zonasi.refresh_zona(conn, tahun)
        conn.commit()
    return {"tahun": tahun, "baris_dibaca": len(baris), "baris_valid": len(baris), "total_kasus": total,
            "peringatan": peringatan, "disimpan": not dry_run}


@router.get("/export", summary="Ekspor ringkasan (csv)")
def ekspor(conn: Conn, format: str = "csv", tahun: int | None = None, jenis: str | None = None, polsek: str | None = None):
    raise belum_diimplementasi("GET /api/export")
