"""
Bersihkan & normalisasi rekap kriminalitas 2024.
Jalankan dari root repo:  python data/scripts/bersihkan_csv.py
Input : data/rekap_kriminalitas_2024.csv   (format asli: No, Polsek, 18 kolom jenis, Jumlah)
Output: data/bersih/  -> polsek.csv, jenis_kejahatan.csv, kasus_kejahatan.csv, rekap_2024_bersih.csv, laporan_validasi.md
Pengecekan gagal -> script berhenti dengan exit code 1 (jangan impor ke DB sebelum lolos).
"""
import sys, re
import pandas as pd

TAHUN = 2024
SRC = "data/rekap_kriminalitas_2024.csv"
OUT = "data/bersih"
EXPECT_POLSEK, EXPECT_JENIS, EXPECT_TOTAL = 27, 18, 1163

# kolom CSV -> (kode, nama lengkap); urutan = id_jenis 1..18
JENIS = [
 ("Aniaya","ANIAYA","Penganiayaan"),("Aniaya Berat","ANIAYA_BERAT","Penganiayaan Berat"),
 ("Curas","CURAS","Pencurian dengan Kekerasan (Curas)"),("Curat","CURAT","Pencurian dengan Pemberatan (Curat)"),
 ("Curanmor R4","CURANMOR_R4","Curanmor Roda 4"),("Curanmor R2","CURANMOR_R2","Curanmor Roda 2"),
 ("Perkosaan","PERKOSAAN","Perkosaan"),("Judi","JUDI","Perjudian"),("Rusak","RUSAK","Perusakan"),
 ("Tipu","TIPU","Penipuan"),("Gelap","GELAP","Penggelapan"),("Curi Biasa","CURI_BIASA","Pencurian Biasa"),
 ("KDRT","KDRT","KDRT"),("Sajam","SAJAM","Senjata Tajam"),("Tdk Senang","TDK_SENANG","Perbuatan Tidak Menyenangkan"),
 ("Keroyok","KEROYOK","Pengeroyokan"),("Cabul","CABUL","Pencabulan"),("Lain2","LAIN2","Lain-lain"),
]

def zona(n): return "tinggi" if n >= 60 else "sedang" if n >= 30 else "rendah"

# Koreksi salah ketik di sumber (dicatat di laporan)
KOREKSI_NAMA = {"Pemeugpeuk": "Pameungpeuk"}

# Usulan nama wilayah resmi (kecamatan Kab. Bandung) untuk mencocokkan poligon GeoJSON.
# VERIFIKASI dengan atribut data BIG/OSM yang dipakai; ubah di sini bila berbeda.
NAMA_RESMI = {
    "Bale Endah": "Baleendah", "Bojong Soang": "Bojongsoang", "Dayeuh Kolot": "Dayeuhkolot",
    "Pasir Jambu": "Pasirjambu", "Solokan Jeruk": "Solokanjeruk",
}

def nama_polsek(s):
    s = re.sub(r"\s+", " ", str(s)).strip()          # rapikan spasi
    s = re.sub(r"^polsek\s+", "", s, flags=re.I)      # buang awalan POLSEK
    s = s.title()                                     # "BALE ENDAH" -> "Bale Endah"
    return KOREKSI_NAMA.get(s, s)

cek, errors, warns = [], [], []
def ok(cond, label, detail=""):
    cek.append((("LULUS" if cond else "GAGAL"), label, detail))
    if not cond: errors.append(label)

df = pd.read_csv(SRC, dtype=str, keep_default_na=False)
df.columns = [c.strip() for c in df.columns]
ok(len(df) == EXPECT_POLSEK, f"Jumlah baris Polsek = {EXPECT_POLSEK}", f"ditemukan {len(df)}")

kolom_jenis = [j[0] for j in JENIS]
ok(all(c in df.columns for c in kolom_jenis), f"{EXPECT_JENIS} kolom jenis kejahatan ada lengkap",
   "hilang: " + ", ".join(c for c in kolom_jenis if c not in df.columns) if not all(c in df.columns for c in kolom_jenis) else "")
extra = [c for c in df.columns if c not in kolom_jenis + ["No","Polsek","Jumlah"]]
ok(not extra, "Tidak ada kolom tak dikenal", ", ".join(extra))

# angka: kosong -> error, non-angka -> error
num_cols = kolom_jenis + ["No","Jumlah"]
bad = []
for c in num_cols:
    s = df[c].str.strip()
    m = ~s.str.fullmatch(r"\d+")
    for i in df.index[m]: bad.append(f"baris {i+2}, kolom {c}: '{df.at[i,c]}'")
ok(not bad, "Semua angka valid (bilangan bulat >= 0, tidak kosong)", "; ".join(bad[:5]))
if bad: 
    for st,l,d in cek: print(st,l,d)
    sys.exit(1)
for c in num_cols: df[c] = df[c].str.strip().astype(int)

df["nama_polsek"] = df["Polsek"].map(nama_polsek)
ok(df["nama_polsek"].is_unique, "Nama Polsek unik (tanpa duplikat)", ", ".join(df["nama_polsek"][df["nama_polsek"].duplicated()]))
ok(df["No"].tolist() == list(range(1, EXPECT_POLSEK+1)), "Kolom No berurutan 1..27 (dipakai sebagai id_polsek)")
ok((df["Polsek"].str.strip() != df["Polsek"]).sum() == 0, "Tidak ada spasi nyasar di nama asli", f"{(df['Polsek'].str.strip() != df['Polsek']).sum()} baris dirapikan" )
hitung = df[kolom_jenis].sum(axis=1)
salah = df[hitung != df["Jumlah"]]
ok(salah.empty, "Kolom Jumlah = jumlah 18 kolom jenis di setiap baris", "; ".join(f"{r.nama_polsek}: tertulis {r.Jumlah}, hitung {hitung[i]}" for i, r in salah.iterrows()))
total = int(hitung.sum())
ok(total == EXPECT_TOTAL, f"Total seluruh kasus = {EXPECT_TOTAL:,}".replace(",", "."), f"hasil {total}")

# ------- output tabel (siap impor ke DB) -------
import os; os.makedirs(OUT, exist_ok=True)
polsek = pd.DataFrame({"id_polsek": df["No"], "nama_polsek": df["nama_polsek"]})
polsek["nama_wilayah_resmi"] = polsek["nama_polsek"].map(lambda n: NAMA_RESMI.get(n, n))
polsek.to_csv(f"{OUT}/polsek.csv", index=False)
jenis = pd.DataFrame([{"id_jenis": i+1, "kode_jenis": k, "nama_jenis": n, "kolom_csv_asli": c} for i,(c,k,n) in enumerate(JENIS)])
jenis.to_csv(f"{OUT}/jenis_kejahatan.csv", index=False)
rows, idk = [], 1
for _, r in df.iterrows():
    for i,(c,_,_) in enumerate(JENIS):
        rows.append({"id_kasus": idk, "id_polsek": int(r["No"]), "id_jenis": i+1, "tahun": TAHUN, "jumlah": int(r[c])}); idk += 1
kasus = pd.DataFrame(rows)
kasus.to_csv(f"{OUT}/kasus_kejahatan.csv", index=False)
ok(len(kasus) == EXPECT_POLSEK*EXPECT_JENIS and kasus["jumlah"].sum() == total, "Tabel kasus_kejahatan = 27 x 18 = 486 baris, total tetap 1.163", f"{len(kasus)} baris, total {kasus['jumlah'].sum()}")

bersih = df[["No","nama_polsek"] + kolom_jenis + ["Jumlah"]].rename(columns={"No":"id_polsek"})
bersih["kategori_zona"] = bersih["Jumlah"].map(zona)
bersih.to_csv(f"{OUT}/rekap_2024_bersih.csv", index=False)

# peringatan non-fatal
nol = [j[0] for j in JENIS if df[j[0]].sum() == 0]
if nol: warns.append(f"Jenis dengan total 0 sepanjang 2024: {', '.join(nol)} (tetap disimpan; jumlah = 0).")
dist = bersih["kategori_zona"].value_counts().to_dict()

lap = ["# Laporan Validasi Data Kriminalitas 2024", "", f"Sumber: `{SRC}`", "", "## Hasil Pengecekan", "", "| Status | Pengecekan | Keterangan |", "|---|---|---|"]
lap += [f"| {s} | {l} | {d} |" for s,l,d in cek]
lap += ["", "## Normalisasi Nama Polsek", "", "Aturan: buang awalan `POLSEK`, rapikan spasi, ubah ke huruf kapital di awal kata.", "", "| id_polsek | Nama asli di CSV | Nama setelah normalisasi | Total kasus | Zona |", "|---|---|---|---|---|"]
lap += [f"| {r.No} | {r.Polsek} | {r.nama_polsek} | {r.Jumlah} | {zona(r.Jumlah)} |" for r in df.itertuples()]
lap += ["", "## Koreksi Salah Ketik", ""] + [f"- `{a}` → `{b}` (sumber CSV: salah ketik)" for a,b in KOREKSI_NAMA.items()]
lap += ["", "## Catatan Pencocokan Poligon", "", "Kolom `nama_wilayah_resmi` di `polsek.csv` adalah USULAN nama kecamatan resmi untuk join dengan GeoJSON. Cek ulang terhadap atribut nama di data BIG/OSM yang dipakai.", "", f"Yang berbeda dari nama Polsek: " + ", ".join(f"{k} → {v}" for k,v in NAMA_RESMI.items())]
lap += ["", f"## Ringkasan", "", f"- Polsek: {len(df)} · Jenis: {len(JENIS)} · Total kasus: {total}",
        f"- Distribusi zona (>=60 tinggi, 30-59 sedang, <30 rendah): tinggi {dist.get('tinggi',0)}, sedang {dist.get('sedang',0)}, rendah {dist.get('rendah',0)}"]
if warns: lap += ["", "## Peringatan (tidak fatal)", ""] + [f"- {w}" for w in warns]
lap += ["", "## Berkas Hasil (`data/bersih/`)", "", "- `polsek.csv` → tabel `polsek` (tanpa kolom `geom`, diisi dari GeoJSON nanti; kolom `nama_wilayah_resmi` untuk join poligon)", "- `jenis_kejahatan.csv` → tabel `jenis_kejahatan`", "- `kasus_kejahatan.csv` → tabel `kasus_kejahatan` (486 baris, termasuk jumlah 0)", "- `rekap_2024_bersih.csv` → versi lebar untuk dicek manual / uji data spasial"]
open(f"{OUT}/laporan_validasi.md","w",encoding="utf-8").write("\n".join(lap)+"\n")

for s,l,d in cek: print(f"[{s}] {l}" + (f" — {d}" if d else ""))
for w in warns: print("[PERINGATAN]", w)
sys.exit(1 if errors else 0)
