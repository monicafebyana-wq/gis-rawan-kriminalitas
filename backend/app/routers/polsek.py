"""Peta utama & popup. Lihat docs/api-contract.md bagian 2.1 dan 2.2."""
from fastapi import APIRouter, Query

from app.db import Conn
from app.errors import tidak_ditemukan
from app.params import daftar_int, daftar_zona
from app.services import rekap

router = APIRouter(tags=["Peta"])


@router.get("/polsek", summary="GeoJSON wilayah Polsek + jumlah kasus + zona")
def peta_polsek(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru"),
    jenis: str | None = Query(None, description="id jenis dipisah koma, mis. 1,16"),
    zona: str | None = Query(None, description="tinggi,sedang,rendah (dipisah koma)"),
    polsek: str | None = Query(None, description="id polsek dipisah koma"),
):
    jenis_l, polsek_l, zona_l = daftar_int(jenis, "jenis"), daftar_int(polsek, "polsek"), daftar_zona(zona)
    t = rekap.tentukan_tahun(conn, tahun)
    rows = rekap.rekap_per_polsek(conn, t, jenis_l, polsek_l, zona_l, dengan_geom=True)
    fitur = [{
        "type": "Feature",
        "geometry": r["geometri"],          # None bila poligon belum diimpor
        "properties": {
            "id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "tahun": t,
            "total_kasus": r["total_kasus"], "total_semua_jenis": r["total_semua_jenis"],
            "kategori_zona": r["kategori_zona"],
            "pusat": None if r["pusat_lat"] is None else {"lat": round(r["pusat_lat"], 5), "lng": round(r["pusat_lng"], 5)},
        },
    } for r in rows]
    return {"type": "FeatureCollection", "features": fitur}


@router.get("/polsek/{id_polsek}", summary="Detail satu Polsek (untuk popup)")
def detail_polsek(id_polsek: int, conn: Conn, tahun: int | None = Query(None, ge=2000, le=2100)):
    t = rekap.tentukan_tahun(conn, tahun)
    r = rekap.rekap_per_polsek(conn, t, polsek=[id_polsek])
    if not r:
        raise tidak_ditemukan(f"Polsek dengan id {id_polsek} tidak ditemukan")
    r = r[0]
    rincian = conn.execute(
        """SELECT j.id_jenis, j.kode_jenis, j.nama_jenis, k.jumlah
           FROM kasus_kejahatan k JOIN jenis_kejahatan j USING (id_jenis)
           WHERE k.id_polsek = %s AND k.tahun = %s AND k.jumlah > 0
           ORDER BY k.jumlah DESC, j.id_jenis""", (id_polsek, t)).fetchall()
    return {"id_polsek": r["id_polsek"], "nama_polsek": r["nama_polsek"], "tahun": t,
            "total_kasus": r["total_semua_jenis"], "kategori_zona": r["kategori_zona"], "rincian_jenis": rincian}
