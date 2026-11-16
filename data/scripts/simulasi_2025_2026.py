"""Buat DATA SIMULASI tahun 2025 dan 2026 (untuk pengembangan/demo; BUKAN data resmi kepolisian).

Keluaran (folder data/simulasi/):
  Rekap_Data_Kriminalitas_2025.csv, Rekap_Data_Kriminalitas_2026.csv   format sama dengan data/rekap_kriminalitas_2024.csv
                                                                          (impor lewat halaman Kelola Data -> Impor CSV, isi tahunnya)
  titik_simulasi_2024_2026.csv   satu baris per kasus, koordinat acak DI DALAM poligon Polsek-nya (untuk heatmap)
                                 kolom: lat,lng,jenis,tanggal,sumber,akurasi,polsek  (sumber=simulasi)

Cara membuat (dari root repo):
    pip install shapely
    python data/scripts/simulasi_2025_2026.py

Aturan simulasi (seed tetap -> hasil selalu sama):
  * jumlah per Polsek x jenis 2025 = Poisson(jumlah 2024 x tren Polsek), tren Polsek ~ lognormal (rata-rata +4%/tahun)
  * 2026 = periode Januari-Oktober saja (10/12 tahun), dengan tren Polsek yang berlanjut
  * titik 2024 memakai jumlah ASLI 2024 (hanya lokasi & tanggalnya yang acak)
GANTI file-file ini dengan data resmi begitu tersedia, lalu hapus catatan tahunnya (DELETE /api/tahun/{tahun}/catatan).
"""
import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from shapely.geometry import Point, shape

DATA = Path(__file__).resolve().parents[1]
SEED = 20260515
JENIS = ["Aniaya", "Aniaya Berat", "Curas", "Curat", "Curanmor R4", "Curanmor R2", "Perkosaan", "Judi", "Rusak", "Tipu",
         "Gelap", "Curi Biasa", "KDRT", "Sajam", "Tdk Senang", "Keroyok", "Cabul", "Lain2"]
KODE = ["ANIAYA", "ANIAYA_BERAT", "CURAS", "CURAT", "CURANMOR_R4", "CURANMOR_R2", "PERKOSAAN", "JUDI", "RUSAK", "TIPU",
        "GELAP", "CURI_BIASA", "KDRT", "SAJAM", "TDK_SENANG", "KEROYOK", "CABUL", "LAIN2"]
HARI_2026 = (date(2026, 10, 31) - date(2026, 1, 1)).days + 1          # Januari-Oktober


def poisson(rng: random.Random, lam: float) -> int:
    batas, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= batas:
            return k
        k += 1


def baca_rekap_2024():
    with open(DATA / "rekap_kriminalitas_2024.csv", encoding="utf-8-sig", newline="") as f:
        return [{"no": int(r["No"]), "polsek": r["Polsek"].strip(), "jumlah": [int(r[j]) for j in JENIS]} for r in csv.DictReader(f)]


def tulis_rekap(path: Path, baris: list[dict]) -> int:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["No", "Polsek", *JENIS, "Jumlah"])
        for b in baris:
            w.writerow([b["no"], b["polsek"], *b["jumlah"], sum(b["jumlah"])])
    return sum(sum(b["jumlah"]) for b in baris)


def main() -> None:
    rng = random.Random(SEED)
    asli = baca_rekap_2024()
    rekap = {2024: asli}
    bobot = {b["no"]: sum(b["jumlah"]) for b in asli}

    def faktor(sigma: float, rata_rata: float) -> dict[int, float]:
        """Faktor perubahan per Polsek ~ lognormal, dinormalkan agar rata-rata berbobot (jumlah 2024) = rata_rata."""
        mentah = {no: rng.lognormvariate(0, sigma) for no in bobot}
        rata = sum(bobot[no] * mentah[no] for no in bobot) / sum(bobot.values())
        return {no: mentah[no] * rata_rata / rata for no in bobot}

    f2025 = faktor(0.18, 1.04)                                    # 2025: naik ~4% dibanding 2024, tiap Polsek berbeda
    f2026 = {no: f2025[no] * g for no, g in faktor(0.10, 1.02).items()}   # 2026 melanjutkan tren 2025 (+2%) ...
    for tahun, faktor_tahun, skala in ((2025, f2025, 1.0), (2026, f2026, 10 / 12)):   # ... tapi hanya 10 bulan (Jan-Okt)
        rekap[tahun] = [{"no": b["no"], "polsek": b["polsek"],
                         "jumlah": [poisson(rng, x * faktor_tahun[b["no"]] * skala + 0.05) for x in b["jumlah"]]} for b in asli]
    out = DATA / "simulasi"
    out.mkdir(exist_ok=True)
    for tahun in (2025, 2026):
        total = tulis_rekap(out / f"Rekap_Data_Kriminalitas_{tahun}.csv", rekap[tahun])
        print(f"Rekap {tahun}: {total} kasus")

    # ---- titik simulasi: acak di dalam poligon Polsek (dikecilkan ~90 m dari tepi agar tidak ambigu di perbatasan)
    geo = json.load(open(DATA / "geojson" / "polsek_poligon.geojson", encoding="utf-8"))
    poligon = {}
    for ft in geo["features"]:
        g = shape(ft["geometry"])
        dalam = g.buffer(-0.0008)
        poligon[ft["properties"]["id_polsek"]] = (ft["properties"]["nama_polsek"], dalam if not dalam.is_empty else g)
    dipakai: set[tuple[float, float]] = set()
    titik = []
    for tahun in (2024, 2025, 2026):
        hari = 366 if tahun == 2024 else (365 if tahun == 2025 else HARI_2026)
        for b in rekap[tahun]:
            nama, g = poligon[b["no"]]
            x0, y0, x1, y1 = g.bounds
            for kode, n in zip(KODE, b["jumlah"]):
                for _ in range(n):
                    while True:
                        lng, lat = round(rng.uniform(x0, x1), 6), round(rng.uniform(y0, y1), 6)
                        if (lat, lng) not in dipakai and g.contains(Point(lng, lat)):
                            dipakai.add((lat, lng))
                            break
                    tgl = date(tahun, 1, 1) + timedelta(days=rng.randrange(hari))
                    titik.append((lat, lng, kode, tgl.isoformat(), "simulasi", "kecamatan", nama))
    titik.sort(key=lambda t: (t[3], t[6], t[2]))
    with open(out / "titik_simulasi_2024_2026.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lng", "jenis", "tanggal", "sumber", "akurasi", "polsek"])
        w.writerows(titik)
    print(f"Titik simulasi: {len(titik)} baris -> {out / 'titik_simulasi_2024_2026.csv'}")


if __name__ == "__main__":
    main()
