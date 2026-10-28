"""Impor CSV (operator/admin) & ekspor laporan CSV/XLSX (publik). Lihat api-contract.md bagian 2.8 & 3.5."""
from typing import Literal

from fastapi import APIRouter, File, Form, Query, Response, UploadFile

from app.db import Conn
from app.deps import Pengguna
from app.errors import validasi_gagal
from app.params import daftar_int
from app.services import audit, ekspor as ekspor_svc, impor_csv as impor_csv_svc, rekap, zonasi

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
        audit.catat(conn, user, "impor", "kasus", tahun, {"berkas": file.filename, "mode": mode, "baris": len(baris), "total_kasus": total})
        conn.commit()
    return {"tahun": tahun, "baris_dibaca": len(baris), "baris_valid": len(baris), "total_kasus": total,
            "peringatan": peringatan, "disimpan": not dry_run}


@router.get("/export", summary="Ekspor rekap kasus per Polsek x jenis (csv / xlsx)")
def ekspor(
    conn: Conn,
    format: Literal["csv", "xlsx"] = Query("csv"),
    tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru"),
    jenis: str | None = Query(None, description="id jenis dipisah koma (kolom jenis yang diekspor)"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
):
    jenis_l, polsek_l = daftar_int(jenis, "jenis"), daftar_int(polsek, "polsek")
    t = rekap.tentukan_tahun(conn, tahun)
    header, baris = ekspor_svc.susun_tabel(conn, t, jenis_l, polsek_l)
    if format == "csv":
        isi, media = ekspor_svc.ke_csv(header, baris), "text/csv; charset=utf-8"
    else:
        isi, media = ekspor_svc.ke_xlsx(header, baris, t), ekspor_svc.XLSX_MEDIA
    return Response(content=isi, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="rekap_kriminalitas_{t}.{format}"'})
