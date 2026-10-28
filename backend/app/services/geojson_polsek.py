"""Impor poligon wilayah Polsek dari GeoJSON lewat API (versi API dari db/seed/import_poligon.sql).

Pencocokan fitur -> Polsek: properties.id_polsek (utama; bila properties.nama_polsek ikut ada, harus cocok dengan database),
atau tanpa id: properties.nama_polsek / nama (juga dicocokkan ke kolom nama_wilayah_resmi).
Semua dalam SATU transaksi: ada pengecekan gagal / dry_run -> dibatalkan, kolom geom tidak berubah.
Boleh mengunggah sebagian Polsek saja (yang tidak ada di berkas dibiarkan).
"""
import json

import psycopg

from app.errors import validasi_gagal
from app.services.impor_csv import normalkan_nama

MAKS_BYTE = 10 * 1024 * 1024
MAKS_ERROR_DITAMPILKAN = 50
BATAS_WILAYAH = (107.2, -7.6, 108.2, -6.6)      # lon_min, lat_min, lon_max, lat_max (Kab. Bandung; sama dengan import_poligon.sql)
LUAS_KM2 = (1, 600)
TOLERANSI_OVERLAP_KM2 = 0.05
TIPE_BOLEH = ("Polygon", "MultiPolygon")
_KUNCI_NAMA = ("nama_polsek", "nama", "NAMA", "name", "NAME")

_SQL_TULIS = """
UPDATE polsek p SET geom = x.geom
FROM (SELECT ST_Multi(ST_CollectionExtract(CASE WHEN ST_IsValid(g) THEN g ELSE ST_MakeValid(g) END, 3)) AS geom,
             ST_IsValid(g) AS valid_asli
      FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON(%(g)s::text), 4326) AS g) s) x
WHERE p.id_polsek = %(id)s
RETURNING x.valid_asli
"""


def baca_fitur(isi: bytes) -> list[dict]:
    if len(isi) > MAKS_BYTE:
        raise validasi_gagal(f"Berkas terlalu besar (maksimal {MAKS_BYTE // 1024 // 1024} MB)", ["file"])
    try:
        data = json.loads(isi.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise validasi_gagal("Berkas bukan JSON/GeoJSON yang valid", ["file"])
    if isinstance(data, dict) and data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list):
        fitur = data["features"]
    elif isinstance(data, dict) and data.get("type") == "Feature":
        fitur = [data]
    else:
        raise validasi_gagal("GeoJSON harus berupa FeatureCollection atau Feature", ["file"])
    if not fitur:
        raise validasi_gagal("GeoJSON tidak berisi fitur", ["file"])
    return fitur


def _potong(errors: list[str]) -> list[str]:
    sisa = len(errors) - MAKS_ERROR_DITAMPILKAN
    return errors[:MAKS_ERROR_DITAMPILKAN] + ([f"...dan {sisa} error lain"] if sisa > 0 else [])


def _cari_polsek(f, per_id: dict[int, dict], per_nama: dict[str, int]) -> tuple[int | None, str | None]:
    props = f.get("properties") if isinstance(f, dict) else None
    props = props if isinstance(props, dict) else {}
    nama = next((props[k] for k in _KUNCI_NAMA if isinstance(props.get(k), str) and props[k].strip()), None)
    if props.get("id_polsek") is not None:
        try:
            id_p = int(props["id_polsek"])
        except (TypeError, ValueError):
            return None, f"properties.id_polsek '{props['id_polsek']}' bukan bilangan bulat"
        if id_p not in per_id:
            return None, f"id_polsek {id_p} tidak ada di database"
        if nama and normalkan_nama(nama).lower() != per_id[id_p]["nama_polsek"].lower():
            return None, (f"nama di GeoJSON ('{nama}') beda dari database ('{per_id[id_p]['nama_polsek']}') "
                          f"untuk id_polsek {id_p} - id/nama tertukar?")
        return id_p, None
    if nama:
        id_p = per_nama.get(normalkan_nama(nama).lower()) or per_nama.get(nama.strip().lower())
        return (id_p, None) if id_p else (None, f"Polsek '{nama}' tidak dikenal")
    return None, "tidak punya properties.id_polsek maupun properties.nama_polsek"


def _verifikasi(conn: psycopg.Connection, ids: list[int], nama_dari_id: dict[int, str]) -> list[str]:
    errors: list[str] = []
    x0, y0, x1, y1 = BATAS_WILAYAH
    dalam_kotak: list[int] = []
    for r in conn.execute(
            """SELECT id_polsek, geom IS NULL OR ST_IsEmpty(geom) AS kosong, COALESCE(ST_IsValid(geom), false) AS valid,
                      ST_XMin(geom) AS a, ST_YMin(geom) AS b, ST_XMax(geom) AS c, ST_YMax(geom) AS d
               FROM polsek WHERE id_polsek = ANY(%s)""", (ids,)).fetchall():
        nama = nama_dari_id[r["id_polsek"]]
        if r["kosong"]:
            errors.append(f"{nama}: geometri kosong / bukan poligon")
        elif not r["valid"]:
            errors.append(f"{nama}: geometri tidak valid dan tidak bisa diperbaiki otomatis")
        elif not (r["a"] >= x0 and r["c"] <= x1 and r["b"] >= y0 and r["d"] <= y1):
            errors.append(f"{nama}: di luar kotak wilayah (lon {x0}-{x1}, lat {y0} s/d {y1}) - lon/lat tertukar atau CRS bukan WGS 84?")
        else:
            dalam_kotak.append(r["id_polsek"])
    if errors:
        return errors
    for r in conn.execute("SELECT id_polsek, ST_Area(geom::geography) / 1e6 AS km2 FROM polsek WHERE id_polsek = ANY(%s)",
                          (dalam_kotak,)).fetchall():
        if not (LUAS_KM2[0] <= r["km2"] <= LUAS_KM2[1]):
            errors.append(f"{nama_dari_id[r['id_polsek']]}: luas {r['km2']:.2f} km2 tidak wajar (harus {LUAS_KM2[0]}-{LUAS_KM2[1]} km2)")
    for r in conn.execute(
            """SELECT a.nama_polsek AS a, b.nama_polsek AS b, ST_Area(ST_Intersection(a.geom, b.geom)::geography) / 1e6 AS km2
               FROM polsek a JOIN polsek b ON a.id_polsek < b.id_polsek AND a.geom && b.geom
               WHERE (a.id_polsek = ANY(%(ids)s) OR b.id_polsek = ANY(%(ids)s))
                 AND ST_Area(ST_Intersection(a.geom, b.geom)::geography) / 1e6 > %(tol)s""",
            {"ids": ids, "tol": TOLERANSI_OVERLAP_KM2}).fetchall():
        errors.append(f"{r['a']} dan {r['b']} tumpang tindih {r['km2']:.2f} km2 (toleransi {TOLERANSI_OVERLAP_KM2} km2)")
    return errors


def terapkan(conn: psycopg.Connection, fitur: list, dry_run: bool) -> dict:
    """Validasi lalu (kalau bukan dry_run) simpan. Error -> validasi_gagal(detail=[...]) dan tidak ada yang tersimpan."""
    polsek = conn.execute("SELECT id_polsek, nama_polsek, nama_wilayah_resmi FROM polsek").fetchall()
    per_id = {p["id_polsek"]: p for p in polsek}
    per_nama: dict[str, int] = {}
    for p in polsek:
        per_nama[p["nama_polsek"].lower()] = p["id_polsek"]
    for p in polsek:
        if p["nama_wilayah_resmi"]:
            per_nama.setdefault(normalkan_nama(p["nama_wilayah_resmi"]).lower(), p["id_polsek"])
    nama_dari_id = {i: p["nama_polsek"] for i, p in per_id.items()}

    errors: list[str] = []
    target: dict[int, tuple[int, dict]] = {}
    for no, f in enumerate(fitur, start=1):
        id_p, err = _cari_polsek(f, per_id, per_nama)
        if err:
            errors.append(f"fitur {no}: {err}")
            continue
        if id_p in target:
            errors.append(f"fitur {no}: Polsek '{nama_dari_id[id_p]}' muncul lebih dari sekali")
            continue
        g = f.get("geometry")
        if not isinstance(g, dict) or g.get("type") not in TIPE_BOLEH or not g.get("coordinates"):
            errors.append(f"fitur {no} ({nama_dari_id[id_p]}): geometri harus Polygon atau MultiPolygon")
            continue
        target[id_p] = (no, g)
    if errors:
        raise validasi_gagal("GeoJSON tidak valid", _potong(errors))

    diperbaiki: list[str] = []
    belum_punya: list[str] = []
    with conn.transaction():                                   # savepoint: dibatalkan bila error / dry_run
        for id_p, (no, g) in target.items():
            try:
                with conn.transaction():
                    valid = conn.execute(_SQL_TULIS, {"g": json.dumps(g), "id": id_p}).fetchone()["valid_asli"]
            except psycopg.Error:
                errors.append(f"fitur {no} ({nama_dari_id[id_p]}): koordinat/geometri tidak bisa dibaca")
                continue
            if not valid:
                diperbaiki.append(nama_dari_id[id_p])
        if not errors:
            errors = _verifikasi(conn, list(target), nama_dari_id)
        belum_punya = [r["nama_polsek"] for r in conn.execute("SELECT nama_polsek FROM polsek WHERE geom IS NULL ORDER BY id_polsek").fetchall()]
        if errors or dry_run:
            raise psycopg.Rollback()
    if errors:
        raise validasi_gagal("GeoJSON tidak valid", _potong(errors))

    peringatan = [f"{len(belum_punya)} Polsek belum punya poligon: {', '.join(belum_punya)}"] if belum_punya else []
    return {"fitur_dibaca": len(fitur),
            "polsek_diperbarui": [{"id_polsek": i, "nama_polsek": nama_dari_id[i]} for i in target],
            "diperbaiki_otomatis": diperbaiki, "peringatan": peringatan, "disimpan": not dry_run}
