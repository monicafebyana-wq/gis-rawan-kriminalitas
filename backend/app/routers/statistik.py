"""Dashboard. Lihat docs/api-contract.md bagian 2.6 & 2.7."""
from fastapi import APIRouter, Query

from app.db import Conn
from app.params import daftar_int
from app.services import rekap

router = APIRouter(tags=["Statistik"])


@router.get("/statistik", summary="Ringkasan dashboard")
def statistik(
    conn: Conn,
    tahun: int | None = Query(None, ge=2000, le=2100, description="default: tahun terbaru"),
    top: int = Query(4, ge=1, le=18, description="jumlah jenis teratas di top_jenis"),
):
    t = rekap.tentukan_tahun(conn, tahun)
    per_polsek = rekap.rekap_per_polsek(conn, t, urut_kasus=True)          # sudah urut kasus terbanyak
    per_jenis = conn.execute(
        """SELECT j.id_jenis, j.kode_jenis, j.nama_jenis, COALESCE(SUM(k.jumlah), 0)::int AS jumlah
           FROM jenis_kejahatan j LEFT JOIN kasus_kejahatan k ON k.id_jenis = j.id_jenis AND k.tahun = %s
           GROUP BY j.id_jenis ORDER BY jumlah DESC, j.id_jenis""", (t,)).fetchall()

    total = sum(p["total_semua_jenis"] for p in per_polsek)
    ringkas = lambda p: {"id_polsek": p["id_polsek"], "nama_polsek": p["nama_polsek"], "total_kasus": p["total_semua_jenis"]}
    top_jenis = per_jenis[:top]
    return {
        "tahun": t,
        "total_kasus": total,
        "jumlah_polsek": len(per_polsek),
        "jumlah_jenis": len(per_jenis),
        "polsek_tertinggi": ringkas(per_polsek[0]) if per_polsek else None,
        "polsek_terendah": ringkas(per_polsek[-1]) if per_polsek else None,
        "distribusi_zona": {z: sum(1 for p in per_polsek if p["kategori_zona"] == z) for z in ("tinggi", "sedang", "rendah")},
        "top_jenis": top_jenis,
        "persen_top_jenis": round(sum(j["jumlah"] for j in top_jenis) / total * 100, 1) if total else 0,
        "per_polsek": [{"id_polsek": p["id_polsek"], "nama_polsek": p["nama_polsek"],
                        "total_kasus": p["total_semua_jenis"], "kategori_zona": p["kategori_zona"]} for p in per_polsek],
        "per_jenis": per_jenis,
    }


@router.get("/statistik/tren", summary="Tren total kasus per tahun")
def tren(conn: Conn, polsek: str | None = Query(None, description="id polsek dipisah koma"),
         jenis: str | None = Query(None, description="id jenis dipisah koma")):
    polsek_l, jenis_l = daftar_int(polsek, "polsek"), daftar_int(jenis, "jenis")
    rows = conn.execute(
        """SELECT tahun::int AS tahun, SUM(jumlah)::int AS total_kasus FROM kasus_kejahatan
           WHERE (%(polsek)s::int[] IS NULL OR id_polsek = ANY(%(polsek)s::int[]))
             AND (%(jenis)s::int[]  IS NULL OR id_jenis  = ANY(%(jenis)s::int[]))
           GROUP BY tahun ORDER BY tahun""", {"polsek": polsek_l, "jenis": jenis_l}).fetchall()
    return {"data": rows}
