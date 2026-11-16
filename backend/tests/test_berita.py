"""Berita yang melengkapi titik kejadian, sumber_data/akurasi, impor CSV dengan kolom berita, catatan per tahun.
Titik uji bertanggal tahun 2099 (dibersihkan otomatis)."""
import psycopg
import pytest

from app.db import conninfo

DALAM = {"lat": -7.0252, "lng": 107.5198, "id_jenis": 4, "tanggal": "2099-03-01"}          # sekitar Soreang
BERITA = {"judul": "Contoh berita uji", "sumber": "Media Uji", "url": "https://contoh.test/berita-1",
          "tanggal_terbit": "2099-03-02", "ringkasan": "Ringkasan uji dengan kalimat sendiri."}


@pytest.fixture()
def bersih(db_hidup):
    def bersihkan():
        with psycopg.connect(conninfo(), autocommit=True) as c:
            c.execute("DELETE FROM titik_kejadian WHERE tanggal >= DATE '2099-01-01'")      # berita ikut terhapus (CASCADE)
            c.execute("DELETE FROM catatan_tahun WHERE tahun = 2099")
    bersihkan()
    yield
    bersihkan()


def titik_dengan_berita(client, header, **ubah):
    r = client.post("/api/titik", json={**DALAM, "berita": BERITA, **ubah}, headers=header["operator"])
    assert r.status_code == 201, r.text
    return r.json()


def test_tambah_titik_sekaligus_berita_tampil_publik(client, header, bersih):
    t = titik_dengan_berita(client, header, sumber="berita", akurasi="kecamatan")
    assert (t["sumber_data"], t["akurasi"], t["jumlah_berita"]) == ("berita", "kecamatan", 1)
    assert t["nama_polsek"] == "Soreang"                                                      # otomatis dari poligon asli

    peta = client.get("/api/berita-kejadian?tahun=2099").json()                               # PUBLIK, tanpa login
    assert peta["type"] == "FeatureCollection" and peta["total"] == 1
    f = peta["features"][0]
    assert f["geometry"] == {"type": "Point", "coordinates": [107.5198, -7.0252]}
    p = f["properties"]
    assert (p["id_titik"], p["nama_jenis"], p["nama_polsek"], p["akurasi"], p["sumber_data"]) == (t["id_titik"], "Pencurian dengan Pemberatan (Curat)", "Soreang", "kecamatan", "berita")
    assert p["berita"][0]["url"] == BERITA["url"] and p["berita"][0]["tanggal_terbit"] == "2099-03-02" and p["berita"][0]["sumber"] == "Media Uji"
    assert client.get("/api/berita-kejadian?tahun=2098").json()["total"] == 0
    assert client.get("/api/berita-kejadian?tahun=2099&jenis=1").json()["total"] == 0          # filter jenis
    assert client.get("/api/berita-kejadian?tahun=2099&polsek=1").json()["total"] == 0         # filter polsek


def test_titik_tanpa_berita_tidak_muncul_di_peta_berita(client, header, bersih):
    client.post("/api/titik", json=DALAM, headers=header["operator"])
    assert client.get("/api/berita-kejadian?tahun=2099").json()["total"] == 0


def test_sumber_berita_wajib_ada_berita(client, header, bersih):
    r = client.post("/api/titik", json={**DALAM, "sumber": "berita"}, headers=header["operator"])
    assert r.status_code == 400 and "berita" in r.json()["error"]["detail"]


@pytest.mark.parametrize("ubah", [
    {"url": "javascript:alert(1)"}, {"url": "ftp://contoh.test/x"}, {"url": "contoh.test/tanpa-skema"}, {"url": "https://spasi di url"},
    {"url": "https://" + "a" * 2000}, {"judul": "ab"}, {"sumber": "x"}, {"ringkasan": "x" * 601}, {"tanggal_terbit": "1999-01-01"}])
def test_validasi_berita(client, header, bersih, ubah):
    r = client.post("/api/titik", json={**DALAM, "berita": {**BERITA, **ubah}}, headers=header["operator"])
    assert r.status_code == 400, r.text


def test_crud_berita_satu_titik(client, header, bersih):
    t = titik_dengan_berita(client, header)
    url = f"/api/titik/{t['id_titik']}/berita"
    assert client.get(url).status_code == 401                                                  # daftar berita per titik: login
    b2 = client.post(url, json={**BERITA, "url": "https://contoh.test/berita-2", "judul": "Berita kedua"}, headers=header["operator"])
    assert b2.status_code == 201
    assert client.post(url, json=BERITA, headers=header["operator"]).status_code == 409        # URL kembar pada titik yang sama
    assert len(client.get(url, headers=header["operator"]).json()["data"]) == 2
    assert client.get(f"/api/titik?tahun=2099&ada_berita=true", headers=header["operator"]).json()["total_data"] == 1

    idb = b2.json()["id_berita"]
    r = client.put(f"/api/berita/{idb}", json={"judul": "Judul diperbarui", "ringkasan": None}, headers=header["operator"])
    assert r.status_code == 200 and r.json()["judul"] == "Judul diperbarui" and r.json()["ringkasan"] is None
    assert client.put(f"/api/berita/{idb}", json={"url": BERITA["url"]}, headers=header["operator"]).status_code == 409
    assert client.put(f"/api/berita/{idb}", json={"url": "javascript:x"}, headers=header["operator"]).status_code == 400
    assert client.put(f"/api/berita/{idb}", json={"judul": None}, headers=header["operator"]).status_code == 400
    assert client.put(f"/api/berita/{idb}", json={}, headers=header["operator"]).status_code == 400
    assert client.put("/api/berita/9999999", json={"judul": "xyz"}, headers=header["operator"]).status_code == 404

    assert client.delete(f"/api/berita/{idb}", headers=header["operator"]).status_code == 403   # hapus: admin saja
    assert client.delete(f"/api/berita/{idb}", headers=header["admin"]).status_code == 204
    assert client.delete(f"/api/berita/{idb}", headers=header["admin"]).status_code == 404
    assert client.post("/api/titik/9999999/berita", json=BERITA, headers=header["operator"]).status_code == 404


def test_hapus_titik_menghapus_beritanya(client, header, bersih):
    t = titik_dengan_berita(client, header)
    assert client.delete(f"/api/titik/{t['id_titik']}", headers=header["admin"]).status_code == 204
    assert client.get("/api/berita-kejadian?tahun=2099").json()["total"] == 0
    with psycopg.connect(conninfo()) as c:
        assert c.execute("SELECT count(*) FROM berita_kejadian WHERE url = %s", (BERITA["url"],)).fetchone()[0] == 0


def test_filter_sumber_di_titik_dan_heatmap(client, header, bersih):
    client.post("/api/titik", json={**DALAM, "sumber": "simulasi", "akurasi": "kecamatan"}, headers=header["operator"])
    titik_dengan_berita(client, header, sumber="berita", lat=-7.03)
    assert client.get("/api/heatmap?tahun=2099").json()["per_sumber"] == {"laporan": 0, "berita": 1, "simulasi": 1}
    assert client.get("/api/titik/sebaran?tahun=2099").json()["per_sumber"] == {"laporan": 0, "berita": 1, "simulasi": 1}
    assert client.get("/api/heatmap?tahun=2099&sumber=simulasi").json()["total_titik"] == 1
    assert client.get("/api/heatmap?tahun=2099&sumber=simulasi,berita").json()["total_titik"] == 2
    assert client.get("/api/heatmap?tahun=2099&sumber=laporan").json()["total_titik"] == 0
    assert client.get("/api/heatmap?tahun=2099").json()["total_titik"] == 2
    assert client.get("/api/heatmap?sumber=asal").status_code == 400
    assert client.get("/api/titik?tahun=2099&sumber=berita", headers=header["operator"]).json()["total_data"] == 1
    d = client.get("/api/titik?tahun=2099&sumber=simulasi", headers=header["operator"]).json()["data"][0]
    assert (d["sumber_data"], d["akurasi"], d["jumlah_berita"]) == ("simulasi", "kecamatan", 0)


def test_ubah_sumber_dan_akurasi(client, header, bersih):
    t = client.post("/api/titik", json=DALAM, headers=header["operator"]).json()
    r = client.put(f"/api/titik/{t['id_titik']}", json={"sumber": "simulasi", "akurasi": "desa"}, headers=header["operator"])
    assert r.status_code == 200 and (r.json()["sumber_data"], r.json()["akurasi"]) == ("simulasi", "desa")
    assert client.put(f"/api/titik/{t['id_titik']}", json={"sumber": "asal"}, headers=header["operator"]).status_code == 400
    assert client.put(f"/api/titik/{t['id_titik']}", json={"akurasi": None}, headers=header["operator"]).status_code == 400


def kirim_csv(client, header, isi, dry_run=False):
    return client.post("/api/titik/import", headers=header["operator"], data={"dry_run": str(dry_run).lower()},
                       files={"file": ("titik.csv", isi.encode(), "text/csv")})


CSV_BERITA = ("lat,lng,jenis,tanggal,sumber,akurasi,polsek,judul_berita,sumber_berita,url_berita,tanggal_berita,ringkasan\n"
              "-7.02,107.52,CURAT,2099-04-01,berita,kecamatan,Soreang,Berita CSV satu,Media Uji,https://contoh.test/csv-1,2099-04-02,Ringkasan satu\n"
              "-6.99,107.62,CURAS,2099-04-03,berita,kecamatan,Pameungpeuk,Berita CSV dua,Media Uji,https://contoh.test/csv-2,,\n"
              "-7.05,107.55,TIPU,2099-04-04,simulasi,kecamatan,,,,,,\n"
              "-7.06,107.56,JUDI,2099-04-05,,,,,,,,\n")


def test_impor_csv_dengan_berita(client, header, bersih):
    r = kirim_csv(client, header, CSV_BERITA, dry_run=True)
    assert r.status_code == 200 and r.json()["disimpan"] is False and r.json()["dengan_berita"] == 2
    assert r.json()["per_sumber"] == {"laporan": 1, "berita": 2, "simulasi": 1}
    assert client.get("/api/berita-kejadian?tahun=2099").json()["total"] == 0                   # dry_run tidak menyimpan
    r = kirim_csv(client, header, CSV_BERITA)
    assert r.status_code == 200 and r.json()["tersimpan"] == 4 and r.json()["dengan_berita"] == 2
    assert any("simulasi" in w for w in r.json()["peringatan"])
    peta = client.get("/api/berita-kejadian?tahun=2099").json()
    assert peta["total"] == 2
    p = {f["properties"]["berita"][0]["url"]: f["properties"] for f in peta["features"]}
    assert p["https://contoh.test/csv-1"]["nama_polsek"] == "Soreang" and p["https://contoh.test/csv-1"]["berita"][0]["ringkasan"] == "Ringkasan satu"
    assert p["https://contoh.test/csv-2"]["nama_polsek"] == "Pameungpeuk"                        # kolom polsek menimpa deteksi poligon
    assert p["https://contoh.test/csv-2"]["berita"][0]["tanggal_terbit"] is None
    assert client.get("/api/titik?tahun=2099&sumber=laporan", headers=header["operator"]).json()["total_data"] == 1
    log = client.get("/api/audit?entitas=titik&aksi=impor&username=uji_operator", headers=header["admin"]).json()["data"][0]["detail"]
    assert log["dengan_berita"] == 2 and log["per_sumber"]["berita"] == 2


@pytest.mark.parametrize("baris, potongan", [
    ("-7.02,107.52,CURAT,2099-04-01,berita,kecamatan,Soreang,,,,,", "wajib disertai url_berita"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,tepat,Soreang,Judul,Media,javascript:alert(1),,", "url_berita harus diawali http"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,tepat,Soreang,,Media,https://contoh.test/x,,", "judul_berita wajib"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,tepat,Soreang,Judul,,https://contoh.test/x,,", "sumber_berita wajib"),
    ("-7.02,107.52,CURAT,2099-04-01,rahasia,tepat,Soreang,,,,,", "sumber 'rahasia' tidak dikenal"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,kira-kira,Soreang,,,,,", "akurasi 'kira-kira' tidak dikenal"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,tepat,Polsek Hantu,,,,,", "polsek 'Polsek Hantu' tidak dikenal"),
    ("-7.02,107.52,CURAT,2099-04-01,laporan,tepat,Soreang,Judul,Media,https://contoh.test/x,31/02/2099,", "tanggal_berita"),
])
def test_impor_csv_berita_tidak_valid(client, header, bersih, baris, potongan):
    r = kirim_csv(client, header, "lat,lng,jenis,tanggal,sumber,akurasi,polsek,judul_berita,sumber_berita,url_berita,tanggal_berita,ringkasan\n" + baris + "\n")
    assert r.status_code == 400 and potongan in " ".join(r.json()["error"]["detail"])
    assert client.get("/api/heatmap?tahun=2099").json()["total_titik"] == 0


def test_catatan_tahun(client, header, bersih):
    awal = client.get("/api/tahun").json()
    assert "catatan" in awal and "2025" in awal["catatan"] and "SIMULASI" in awal["catatan"]["2025"]        # dari migrasi 006
    assert client.put("/api/tahun/2099/catatan", json={"catatan": "Catatan uji"}).status_code == 401
    assert client.put("/api/tahun/2099/catatan", json={"catatan": "Catatan uji"}, headers=header["operator"]).status_code == 403
    r = client.put("/api/tahun/2099/catatan", json={"catatan": "  Data uji coba  "}, headers=header["admin"])
    assert r.status_code == 200 and r.json() == {"tahun": 2099, "catatan": "Data uji coba"}
    assert client.get("/api/tahun").json()["catatan"]["2099"] == "Data uji coba"
    assert client.put("/api/tahun/2099/catatan", json={"catatan": "ab"}, headers=header["admin"]).status_code == 400
    assert client.put("/api/tahun/1900/catatan", json={"catatan": "Salah tahun"}, headers=header["admin"]).status_code == 400
    assert client.delete("/api/tahun/2099/catatan", headers=header["operator"]).status_code == 403
    assert client.delete("/api/tahun/2099/catatan", headers=header["admin"]).status_code == 204
    assert client.delete("/api/tahun/2099/catatan", headers=header["admin"]).status_code == 404
    assert "2099" not in client.get("/api/tahun").json()["catatan"]
    log = client.get("/api/audit?entitas=tahun&username=uji_admin", headers=header["admin"]).json()["data"]
    assert {x["aksi"] for x in log} >= {"ubah", "hapus"}


def test_titik_sebaran_rincian_jenis_dan_filter_sumber(client, header, bersih):
    """/api/titik/sebaran (dipakai lapisan 'titik kejadian' di peta) tetap jalan + mendukung filter sumber."""
    for jenis, lat in ((4, -7.0252), (4, -7.0252), (6, -7.0252), (4, -7.2)):
        client.post("/api/titik", json={**DALAM, "id_jenis": jenis, "lat": lat, "lng": 107.5198 if lat > -7.1 else 107.4}, headers=header["operator"])
    j = client.get("/api/titik/sebaran?tahun=2099&grid=0.01").json()
    assert j["total_titik"] == 4 and j["grid_derajat"] == 0.01
    teratas = max(j["data"], key=lambda d: d["bobot"])
    assert teratas["bobot"] == 3 and [r["jumlah"] for r in teratas["rincian"]] == [2, 1]        # 2 curat + 1 curanmor, urut terbanyak
    assert client.get("/api/titik/sebaran?tahun=2099&sumber=simulasi").json()["total_titik"] == 0
    assert client.get("/api/titik/sebaran?tahun=2099&sumber=laporan").json()["total_titik"] == 4
    assert client.get("/api/titik/sebaran?sumber=salah").status_code == 400
