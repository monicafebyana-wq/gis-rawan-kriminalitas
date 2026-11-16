import { useCallback, useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Titik Kejadian (admin/operator): koordinat tiap kejadian untuk heatmap di halaman Peta.
// Data ini terpisah dari rekap kasus, jadi tidak mengubah jumlah kasus maupun warna zona.
// Tiap titik punya sumber (laporan / berita / simulasi), akurasi lokasi, dan boleh dilengkapi berita (tautan).
// Endpoint: GET/POST /api/titik, PUT/DELETE /api/titik/{id}, POST /api/titik/import, /api/titik/{id}/berita, /api/berita/{id}.
const BATAS = 20;
const PUSAT_AWAL = [-7.05, 107.55];
const hariIni = () => new Date().toISOString().slice(0, 10);
const FORM_KOSONG = () => ({ lat: '', lng: '', id_jenis: '', tanggal: hariIni(), id_polsek: '', sumber: 'laporan', akurasi: 'tepat' });
const BERITA_KOSONG = { judul: '', sumber: '', url: '', tanggal_terbit: '', ringkasan: '' };
const SUMBER = { laporan: 'Laporan', berita: 'Berita', simulasi: 'Simulasi' };
const WARNA_SUMBER = { laporan: 'success', berita: 'info', simulasi: 'secondary' };
const AKURASI = { tepat: 'Tepat (koordinat TKP)', desa: 'Perkiraan desa', kecamatan: 'Perkiraan kecamatan' };
const aman = (u) => /^https?:\/\//i.test(u); // tautan hanya http/https

// Isian berita -> body API (kolom opsional yang kosong tidak dikirim).
function bodyBerita(b) {
  const body = { judul: b.judul.trim(), sumber: b.sumber.trim(), url: b.url.trim() };
  if (b.tanggal_terbit) body.tanggal_terbit = b.tanggal_terbit;
  if (b.ringkasan.trim()) body.ringkasan = b.ringkasan.trim();
  return body;
}

function BeritaFields({ nilai, ubah, awalan }) {
  return (
    <>
      <div className="mb-2">
        <label className="form-label small fw-semibold" htmlFor={`${awalan}-judul`}>Judul ringkas</label>
        <input id={`${awalan}-judul`} className="form-control form-control-sm" maxLength={300} value={nilai.judul}
          placeholder="tulis dengan kalimat sendiri" onChange={(e) => ubah({ ...nilai, judul: e.target.value })} />
      </div>
      <div className="row g-2 mb-2">
        <div className="col-6">
          <label className="form-label small fw-semibold" htmlFor={`${awalan}-media`}>Media</label>
          <input id={`${awalan}-media`} className="form-control form-control-sm" maxLength={100} value={nilai.sumber}
            placeholder="mis. ANTARA" onChange={(e) => ubah({ ...nilai, sumber: e.target.value })} />
        </div>
        <div className="col-6">
          <label className="form-label small fw-semibold" htmlFor={`${awalan}-tgl`}>Tanggal terbit</label>
          <input id={`${awalan}-tgl`} type="date" className="form-control form-control-sm" value={nilai.tanggal_terbit}
            onChange={(e) => ubah({ ...nilai, tanggal_terbit: e.target.value })} />
        </div>
      </div>
      <div className="mb-2">
        <label className="form-label small fw-semibold" htmlFor={`${awalan}-url`}>Tautan berita</label>
        <input id={`${awalan}-url`} type="url" className="form-control form-control-sm" maxLength={2000} value={nilai.url}
          placeholder="https://…" onChange={(e) => ubah({ ...nilai, url: e.target.value })} />
      </div>
      <div className="mb-2">
        <label className="form-label small fw-semibold" htmlFor={`${awalan}-ring`}>Ringkasan (opsional)</label>
        <textarea id={`${awalan}-ring`} rows={2} className="form-control form-control-sm" maxLength={600} value={nilai.ringkasan}
          placeholder="1-2 kalimat dengan kata sendiri (jangan menyalin teks berita)" onChange={(e) => ubah({ ...nilai, ringkasan: e.target.value })} />
      </div>
    </>
  );
}

// Daftar berita satu titik (mode ubah): tambah berita, hapus (admin).
function BeritaTitik({ token, idTitik, adalahAdmin, onUbah }) {
  const [daftar, setDaftar] = useState([]);
  const [baru, setBaru] = useState(BERITA_KOSONG);
  const [galat, setGalat] = useState('');
  const [sibuk, setSibuk] = useState(false);

  const muat = useCallback(
    () => api.daftarBerita(token, idTitik).then((r) => setDaftar(r.data)).catch((e) => setGalat(e.message)),
    [token, idTitik]
  );
  useEffect(() => {
    muat();
  }, [muat]);

  async function tambah(e) {
    e.preventDefault();
    setGalat('');
    setSibuk(true);
    try {
      await api.tambahBerita(token, idTitik, bodyBerita(baru));
      setBaru(BERITA_KOSONG);
      await muat();
      onUbah();
    } catch (err) {
      setGalat(`Gagal menambah berita: ${err.message}${err.status === 400 && err.detail?.length ? ` (${err.detail.join(', ')})` : ''}`);
    } finally {
      setSibuk(false);
    }
  }

  async function hapus(b) {
    if (!window.confirm(`Hapus berita ini dari titik?\n\n${b.judul}`)) return;
    setGalat('');
    try {
      await api.hapusBerita(token, b.id_berita);
      await muat();
      onUbah();
    } catch (err) {
      setGalat(`Gagal menghapus berita: ${err.message}`);
    }
  }

  return (
    <div className="card card-body">
      <h2 className="h5">Berita titik ini</h2>
      {daftar.length === 0 && <p className="small text-secondary">Belum ada berita.</p>}
      {daftar.map((b) => (
        <div className="mb-2 pb-2 border-bottom" key={b.id_berita}>
          {aman(b.url) ? (
            <a href={b.url} target="_blank" rel="noopener noreferrer" className="fw-semibold">{b.judul}</a>
          ) : (
            <span className="fw-semibold">{b.judul}</span>
          )}
          <div className="small text-secondary">{b.sumber}{b.tanggal_terbit && ` · ${b.tanggal_terbit}`}</div>
          {b.ringkasan && <div className="small">{b.ringkasan}</div>}
          {adalahAdmin && (
            <button type="button" className="btn btn-outline-danger btn-sm mt-1" onClick={() => hapus(b)}>Hapus berita</button>
          )}
        </div>
      ))}
      {galat && <div className="alert alert-danger py-2 small" role="alert">{galat}</div>}
      <form onSubmit={tambah}>
        <div className="fw-semibold small mb-2">Tambah berita</div>
        <BeritaFields nilai={baru} ubah={setBaru} awalan="tbe" />
        <button className="btn btn-outline-primary btn-sm" type="submit"
          disabled={sibuk || !baru.judul.trim() || !baru.sumber.trim() || !baru.url.trim()}>
          {sibuk ? 'Menyimpan…' : 'Tambah berita'}
        </button>
      </form>
    </div>
  );
}

function KlikPilih({ onPilih }) {
  useMapEvents({ click: (e) => onPilih(e.latlng.lat, e.latlng.lng) });
  return null;
}

export default function TitikPage() {
  const { sesi } = useAuth();
  const token = sesi.token;
  const adalahAdmin = sesi.pengguna.peran === 'admin';

  const [daftarTahun, setDaftarTahun] = useState([]);
  const [daftarJenis, setDaftarJenis] = useState([]);
  const [daftarPolsek, setDaftarPolsek] = useState([]);

  const [filter, setFilter] = useState({ tahun: '', jenis: '', polsek: '', sumber: '', ada_berita: '' });
  const [halaman, setHalaman] = useState(1);
  const [hasil, setHasil] = useState(null);
  const [memuat, setMemuat] = useState(false);
  const [versi, setVersi] = useState(0);
  const [pesan, setPesan] = useState(null);

  const [form, setForm] = useState(FORM_KOSONG);
  const [beritaBaru, setBeritaBaru] = useState(BERITA_KOSONG); // berita opsional saat menambah titik
  const [editId, setEditId] = useState(null);
  const [awal, setAwal] = useState(null); // nilai asli titik yang sedang diubah
  const [sedangSimpan, setSedangSimpan] = useState(false);

  const [berkas, setBerkas] = useState(null);
  const [sedangImpor, setSedangImpor] = useState(false);
  const [hasilImpor, setHasilImpor] = useState(null);

  const muatUlang = () => setVersi((v) => v + 1);

  useEffect(() => {
    Promise.all([api.tahun(), api.jenis(), api.polsek()])
      .then(([t, j, p]) => {
        setDaftarTahun(t.data);
        setDaftarJenis(j.data);
        setDaftarPolsek(
          p.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        );
      })
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }));
  }, []);

  useEffect(() => {
    setMemuat(true);
    api
      .titik(token, { ...filter, page: halaman, limit: BATAS })
      .then((r) => {
        if (r.data.length === 0 && halaman > 1) setHalaman(halaman - 1);
        else setHasil(r);
      })
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [token, filter, halaman, versi]);

  function ubahFilter(kunci, nilai) {
    setFilter((f) => ({ ...f, [kunci]: nilai })); // bentuk fungsi: aman bila dua filter berubah berurutan
    setHalaman(1);
  }

  function galat(e, awalan) {
    if (e.status === 403) return 'Peran kamu tidak diizinkan melakukan ini.';
    const rinci = e.detail && e.detail.length ? ` (${e.detail.join(', ')})` : '';
    return `${awalan}${e.message}${e.status === 400 ? rinci : ''}`;
  }

  function mulaiUbah(t) {
    setEditId(t.id_titik);
    setAwal(t);
    setForm({ lat: String(t.lat), lng: String(t.lng), id_jenis: String(t.id_jenis), tanggal: t.tanggal, id_polsek: '', sumber: t.sumber_data, akurasi: t.akurasi });
    setPesan(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function batalUbah() {
    setEditId(null);
    setAwal(null);
    setForm(FORM_KOSONG());
  }

  async function simpan(e) {
    e.preventDefault();
    setPesan(null);
    const lat = Number(form.lat);
    const lng = Number(form.lng);
    if (form.lat === '' || form.lng === '' || Number.isNaN(lat) || Number.isNaN(lng)) {
      return setPesan({ tipe: 'danger', teks: 'Isi lintang dan bujur, atau klik titiknya di peta kecil.' });
    }
    setSedangSimpan(true);
    try {
      if (editId) {
        // Kirim hanya yang berubah; lat dan lng selalu berpasangan.
        const body = {};
        if (lat !== awal.lat || lng !== awal.lng) Object.assign(body, { lat, lng });
        if (Number(form.id_jenis) !== awal.id_jenis) body.id_jenis = Number(form.id_jenis);
        if (form.tanggal !== awal.tanggal) body.tanggal = form.tanggal;
        if (form.id_polsek) body.id_polsek = Number(form.id_polsek);
        if (form.sumber !== awal.sumber_data) body.sumber = form.sumber;
        if (form.akurasi !== awal.akurasi) body.akurasi = form.akurasi;
        if (Object.keys(body).length === 0) {
          setPesan({ tipe: 'danger', teks: 'Belum ada yang diubah.' });
          return;
        }
        await api.ubahTitik(token, editId, body);
        setPesan({ tipe: 'success', teks: 'Titik kejadian diperbarui.' });
        batalUbah();
      } else {
        const body = { lat, lng, id_jenis: Number(form.id_jenis), tanggal: form.tanggal, sumber: form.sumber, akurasi: form.akurasi };
        if (form.id_polsek) body.id_polsek = Number(form.id_polsek);
        if (beritaBaru.judul.trim() || beritaBaru.sumber.trim() || beritaBaru.url.trim()) body.berita = bodyBerita(beritaBaru);
        if (form.sumber === 'berita' && !body.berita) {
          return setPesan({ tipe: 'danger', teks: 'Titik bersumber "Berita" wajib diisi beritanya (judul, media, dan tautan).' });
        }
        const r = await api.tambahTitik(token, body);
        setBeritaBaru(BERITA_KOSONG);
        setPesan({
          tipe: 'success',
          teks: r.nama_polsek
            ? `Titik disimpan, wilayah terdeteksi: Polsek ${r.nama_polsek}.`
            : 'Titik disimpan. Lokasinya di luar semua wilayah Polsek (tetap tampil di heatmap).',
        });
        setForm({ ...FORM_KOSONG(), id_jenis: form.id_jenis, tanggal: form.tanggal, sumber: form.sumber, akurasi: form.akurasi }); // siap input berikutnya
      }
      muatUlang();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menyimpan titik: ') });
    } finally {
      setSedangSimpan(false);
    }
  }

  async function hapus(t) {
    if (!window.confirm(`Hapus titik ini?\n\n${t.nama_jenis} · ${t.tanggal}\n${t.lat.toFixed(5)}, ${t.lng.toFixed(5)}\n\nTindakan ini tidak bisa dibatalkan.`)) return;
    setPesan(null);
    try {
      await api.hapusTitik(token, t.id_titik);
      if (editId === t.id_titik) batalUbah();
      setPesan({ tipe: 'success', teks: 'Titik dihapus.' });
      muatUlang();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menghapus titik: ') });
    }
  }

  async function impor(hanyaPeriksa) {
    if (!berkas) {
      setHasilImpor({ tipe: 'gagal', pesan: 'Pilih berkas CSV dulu.', detail: [] });
      return;
    }
    const f = new FormData();
    f.append('file', berkas);
    f.append('dry_run', String(hanyaPeriksa));
    setSedangImpor(true);
    setHasilImpor(null);
    try {
      const r = await api.imporTitik(token, f);
      setHasilImpor({ tipe: 'ok', data: r, hanyaPeriksa });
      if (!hanyaPeriksa) muatUlang();
    } catch (err) {
      setHasilImpor({ tipe: 'gagal', pesan: galat(err, ''), detail: err.detail || [] });
    } finally {
      setSedangImpor(false);
    }
  }

  const total = hasil ? hasil.total_data : 0;
  const jumlahHalaman = Math.max(1, Math.ceil(total / BATAS));
  const adaTitikPilihan = form.lat !== '' && form.lng !== '' && !Number.isNaN(Number(form.lat)) && !Number.isNaN(Number(form.lng));

  return (
    <>
      <div className="mb-3">
        <h1 className="h3 mb-1">Titik Kejadian</h1>
        <div className="small text-secondary">
          Lokasi tiap kejadian untuk <strong>heatmap</strong> dan lapisan <strong>berita</strong> di halaman Peta. Terpisah dari rekap kasus:
          menambah titik tidak mengubah jumlah kasus maupun warna zona. Tandai sumbernya dengan jujur: data contoh harus bersumber
          "Simulasi".
          {!adalahAdmin && ' Operator boleh menambah dan mengubah, tidak boleh menghapus.'}
        </div>
      </div>

      {pesan && (
        <div className={`alert alert-${pesan.tipe} alert-dismissible py-2`} role="alert">
          {pesan.teks}
          <button type="button" className="btn-close" aria-label="Tutup" onClick={() => setPesan(null)} />
        </div>
      )}

      <div className="row g-3">
        <div className="col-12 col-xl-8 order-2 order-xl-1">
          <div className="card">
            <div className="card-body">
              <h2 className="h5">Daftar titik</h2>
              <div className="row g-2 mb-3">
                <div className="col-4 col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="tk-tahun">Tahun</label>
                  <select id="tk-tahun" className="form-select form-select-sm" value={filter.tahun} onChange={(e) => ubahFilter('tahun', e.target.value)}>
                    <option value="">Semua</option>
                    {daftarTahun.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="col-8 col-md-4">
                  <label className="form-label small fw-semibold" htmlFor="tk-polsek">Polsek</label>
                  <select id="tk-polsek" className="form-select form-select-sm" value={filter.polsek} onChange={(e) => ubahFilter('polsek', e.target.value)}>
                    <option value="">Semua</option>
                    {daftarPolsek.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
                  </select>
                </div>
                <div className="col-12 col-md-5">
                  <label className="form-label small fw-semibold" htmlFor="tk-jenis">Jenis kejahatan</label>
                  <select id="tk-jenis" className="form-select form-select-sm" value={filter.jenis} onChange={(e) => ubahFilter('jenis', e.target.value)}>
                    <option value="">Semua</option>
                    {daftarJenis.map((j) => <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>)}
                  </select>
                </div>
                <div className="col-6 col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="tk-sumber">Sumber</label>
                  <select id="tk-sumber" className="form-select form-select-sm" value={filter.sumber} onChange={(e) => ubahFilter('sumber', e.target.value)}>
                    <option value="">Semua</option>
                    {Object.entries(SUMBER).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div className="col-6 col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="tk-berita">Berita</label>
                  <select id="tk-berita" className="form-select form-select-sm" value={filter.ada_berita} onChange={(e) => ubahFilter('ada_berita', e.target.value)}>
                    <option value="">Semua</option>
                    <option value="true">Punya berita</option>
                    <option value="false">Belum ada berita</option>
                  </select>
                </div>
              </div>

              <div className="table-responsive">
                <table className="table table-sm table-hover align-middle mb-2 tabel-admin">
                  <thead>
                    <tr>
                      <th>Tanggal</th>
                      <th>Jenis</th>
                      <th className="d-none d-lg-table-cell">Sumber</th>
                      <th className="d-none d-md-table-cell">Polsek</th>
                      <th className="d-none d-sm-table-cell">Koordinat</th>
                      <th className="text-end">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hasil && hasil.data.length === 0 && (
                      <tr><td colSpan="6" className="text-center text-secondary py-3">Belum ada titik yang cocok.</td></tr>
                    )}
                    {hasil && hasil.data.map((t) => (
                      <tr key={t.id_titik} className={editId === t.id_titik ? 'table-warning' : ''}>
                        <td>{t.tanggal}</td>
                        <td>{t.nama_jenis}</td>
                        <td className="d-none d-lg-table-cell">
                          <span className={`badge text-bg-${WARNA_SUMBER[t.sumber_data] || 'secondary'}`}>{SUMBER[t.sumber_data] || t.sumber_data}</span>
                          {t.jumlah_berita > 0 && <>{' '}<span className="small text-secondary">{t.jumlah_berita} berita</span></>}
                        </td>
                        <td className="d-none d-md-table-cell">{t.nama_polsek || <span className="text-secondary" title="Di luar semua wilayah Polsek">—</span>}</td>
                        <td className="d-none d-sm-table-cell small">{t.lat.toFixed(5)}, {t.lng.toFixed(5)}</td>
                        <td className="text-end">
                          <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                            <button type="button" className="btn btn-outline-primary btn-sm" onClick={() => mulaiUbah(t)}>Ubah</button>
                            {adalahAdmin && (
                              <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => hapus(t)}>Hapus</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
                <div className="small text-secondary">
                  {memuat ? 'Memuat…' : `${total} titik · halaman ${halaman} dari ${jumlahHalaman}`}
                </div>
                <div className="btn-group btn-group-sm">
                  <button type="button" className="btn btn-outline-secondary" disabled={halaman <= 1} onClick={() => setHalaman(halaman - 1)}>‹ Sebelumnya</button>
                  <button type="button" className="btn btn-outline-secondary" disabled={halaman >= jumlahHalaman} onClick={() => setHalaman(halaman + 1)}>Berikutnya ›</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 col-xl-4 order-1 order-xl-2 d-flex flex-column gap-3">
          <form className="card card-body" onSubmit={simpan}>
            <h2 className="h5">{editId ? 'Ubah titik' : 'Tambah titik'}</h2>
            <p className="small text-secondary mb-2">Klik peta kecil untuk mengisi koordinat, atau ketik langsung.</p>

            <MapContainer center={PUSAT_AWAL} zoom={9} scrollWheelZoom={false} className="peta-pilih mb-2">
              <TileLayer attribution="&copy; OpenStreetMap" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <KlikPilih onPilih={(la, ln) => setForm((f) => ({ ...f, lat: la.toFixed(6), lng: ln.toFixed(6) }))} />
              {adaTitikPilihan && (
                <CircleMarker
                  center={[Number(form.lat), Number(form.lng)]}
                  radius={8}
                  pathOptions={{ color: '#2a1b13', weight: 2, fillColor: '#c4601a', fillOpacity: 0.9 }}
                />
              )}
            </MapContainer>

            <div className="row g-2 mb-2">
              <div className="col-6">
                <label className="form-label small fw-semibold" htmlFor="tt-lat">Lintang (lat)</label>
                <input id="tt-lat" type="number" step="any" inputMode="decimal" className="form-control form-control-sm" required
                  placeholder="-7.02" value={form.lat} onChange={(e) => setForm({ ...form, lat: e.target.value })} />
              </div>
              <div className="col-6">
                <label className="form-label small fw-semibold" htmlFor="tt-lng">Bujur (lng)</label>
                <input id="tt-lng" type="number" step="any" inputMode="decimal" className="form-control form-control-sm" required
                  placeholder="107.55" value={form.lng} onChange={(e) => setForm({ ...form, lng: e.target.value })} />
              </div>
            </div>
            <div className="mb-2">
              <label className="form-label small fw-semibold" htmlFor="tt-jenis">Jenis kejahatan</label>
              <select id="tt-jenis" className="form-select form-select-sm" required value={form.id_jenis} onChange={(e) => setForm({ ...form, id_jenis: e.target.value })}>
                <option value="">Pilih jenis…</option>
                {daftarJenis.map((j) => <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>)}
              </select>
            </div>
            <div className="row g-2 mb-3">
              <div className="col-5">
                <label className="form-label small fw-semibold" htmlFor="tt-tgl">Tanggal</label>
                <input id="tt-tgl" type="date" className="form-control form-control-sm" required min="2000-01-01" max="2100-12-31"
                  value={form.tanggal} onChange={(e) => setForm({ ...form, tanggal: e.target.value })} />
              </div>
              <div className="col-7">
                <label className="form-label small fw-semibold" htmlFor="tt-polsek">Polsek</label>
                <select id="tt-polsek" className="form-select form-select-sm" value={form.id_polsek} onChange={(e) => setForm({ ...form, id_polsek: e.target.value })}>
                  <option value="">{editId ? 'Tidak diubah / otomatis' : 'Otomatis dari lokasi'}</option>
                  {daftarPolsek.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
                </select>
              </div>
            </div>

            <div className="row g-2 mb-3">
              <div className="col-5">
                <label className="form-label small fw-semibold" htmlFor="tt-sumber">Sumber data</label>
                <select id="tt-sumber" className="form-select form-select-sm" value={form.sumber} onChange={(e) => setForm({ ...form, sumber: e.target.value })}>
                  {Object.entries(SUMBER).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div className="col-7">
                <label className="form-label small fw-semibold" htmlFor="tt-akurasi">Akurasi lokasi</label>
                <select id="tt-akurasi" className="form-select form-select-sm" value={form.akurasi} onChange={(e) => setForm({ ...form, akurasi: e.target.value })}>
                  {Object.entries(AKURASI).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
            </div>

            {!editId && (
              <details className="mb-3" open={form.sumber === 'berita'}>
                <summary className="small fw-semibold mb-2">Lengkapi dengan berita (opsional)</summary>
                <BeritaFields nilai={beritaBaru} ubah={setBeritaBaru} awalan="tb" />
              </details>
            )}

            <div className="d-flex gap-2">
              <button className="btn btn-primary btn-sm" type="submit" disabled={sedangSimpan}>
                {labelSimpan(sedangSimpan, editId)}
              </button>
              {editId && <button type="button" className="btn btn-outline-secondary btn-sm" onClick={batalUbah}>Batal</button>}
            </div>
          </form>

          {editId && <BeritaTitik key={editId} token={token} idTitik={editId} adalahAdmin={adalahAdmin} onUbah={muatUlang} />}

          <div className="card">
            <div className="card-body">
              <h2 className="h5">Impor titik dari CSV</h2>
              <p className="small text-secondary">
                Kolom: <code>lat, lng, jenis, tanggal</code>. <code>jenis</code> boleh kode (CURAT), nama, atau id.
                Tanggal <code>YYYY-MM-DD</code> atau <code>DD/MM/YYYY</code>. Pemisah koma atau titik koma. Maks. 5 MB / 20.000 baris.
                Kolom opsional: <code>sumber</code> (laporan/berita/simulasi), <code>akurasi</code> (tepat/desa/kecamatan),{' '}
                <code>polsek</code>, dan untuk berita: <code>judul_berita, sumber_berita, url_berita, tanggal_berita, ringkasan</code>.
                Semua baris valid atau tidak ada yang disimpan.
              </p>
              <input type="file" accept=".csv,text/csv" className="form-control form-control-sm mb-2"
                onChange={(e) => { setBerkas(e.target.files[0] || null); setHasilImpor(null); }} />
              <div className="d-grid gap-2">
                <button type="button" className="btn btn-outline-primary btn-sm" disabled={sedangImpor} onClick={() => impor(true)}>
                  1. Periksa dulu (tidak menyimpan)
                </button>
                <button type="button" className="btn btn-primary btn-sm" disabled={sedangImpor} onClick={() => impor(false)}>
                  2. Simpan ke database
                </button>
              </div>
              {sedangImpor && <div className="small text-secondary mt-2">Memproses berkas…</div>}

              {hasilImpor && hasilImpor.tipe === 'ok' && (
                <div className="alert alert-success mt-3 mb-0 py-2 small" role="status">
                  <strong>{hasilImpor.hanyaPeriksa ? 'Berkas valid (belum disimpan).' : 'Berhasil disimpan.'}</strong>
                  <div>{hasilImpor.data.baris_dibaca} baris · {hasilImpor.data.tersimpan} tersimpan · {hasilImpor.data.tanpa_polsek} di luar wilayah Polsek · {hasilImpor.data.dengan_berita || 0} dengan berita</div>
                  {hasilImpor.data.peringatan.length > 0 && (
                    <ul className="mb-0 mt-1 ps-3">{hasilImpor.data.peringatan.map((w, i) => <li key={i}>{w}</li>)}</ul>
                  )}
                </div>
              )}
              {hasilImpor && hasilImpor.tipe === 'gagal' && (
                <div className="alert alert-danger mt-3 mb-0 py-2 small" role="alert">
                  <strong>{hasilImpor.pesan || 'Impor gagal.'}</strong>
                  {hasilImpor.detail.length > 0 && (
                    <ul className="mb-0 mt-1 ps-3">{hasilImpor.detail.map((d, i) => <li key={i}>{d}</li>)}</ul>
                  )}
                  <div className="mt-1">Tidak ada data yang diubah. Perbaiki berkasnya lalu coba lagi.</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function labelSimpan(sedang, editId) {
  if (sedang) return 'Menyimpan…';
  return editId ? 'Simpan perubahan' : 'Simpan titik';
}
