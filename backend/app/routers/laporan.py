"""Impor CSV (admin) & ekspor laporan. TODO: impor (No 26), ekspor (No 33). Lihat api-contract.md bagian 2.8 & 3.5."""
from fastapi import APIRouter, File, Form, UploadFile

from app.db import Conn
from app.errors import belum_diimplementasi

router = APIRouter(tags=["Laporan"])


@router.post("/import/csv", summary="Impor rekap CSV (operator/admin)")
def impor_csv(
    conn: Conn,
    file: UploadFile = File(...),
    tahun: int = Form(...),
    mode: str = Form("timpa"),
    dry_run: bool = Form(False),
):
    raise belum_diimplementasi("POST /api/import/csv")


@router.get("/export", summary="Ekspor ringkasan (csv)")
def ekspor(conn: Conn, format: str = "csv", tahun: int | None = None, jenis: str | None = None, polsek: str | None = None):
    raise belum_diimplementasi("GET /api/export")
