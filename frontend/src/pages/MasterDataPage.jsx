import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Master Data (khusus admin): kelola daftar Polsek, poligon wilayahnya, jenis kejahatan, dan catatan per tahun data.
// Endpoint: POST/PUT/DELETE /api/polsek, POST /api/polsek/geojson, POST/PUT/DELETE /api/jenis.
// Aturan dari server: Polsek yang masih punya data kasus dan jenis baku (dipakai impor CSV) tidak bisa dihapus.

function galat(e, awalan) {
  if (e.status === 403) return 'Peran kamu tidak diizinkan melakukan ini.';
  const rinci = e.status === 400 && e.detail && e.detail.length ? ` (${e.detail.join(', ')})` : '';
  return `${awalan}${e.message}${rinci}`;
}

function Pesan({ pesan, tutup }) {
  if (!pesan) return null;
  return (
    <div className={`alert alert-${pesan.tipe} alert-dismissible py-2`} role="alert">
      {pesan.teks}
      <button type="button" className="btn-close" aria-label="Tutup" onClick={tutup} />
    </div>
  );
}

// ---------------------------------------------------------------- Tab Polsek + poligon
function TabPolsek({ token, setPesan }) {
  const [daftar, setDaftar] = useState([]); // { id, nama, punyaPoligon }
  const [memuat, setMemuat] = useState(true);
  const [baru, setBaru] = useState({ nama_polsek: '', nama_wilayah_resmi: '' });
  const [ubahId, setUbahId] = useState(null);
  const [ubahNama, setUbahNama] = useState('');

  const [berkas, setBerkas] = useState(null);
  const [sedangUnggah, setSedangUnggah] = useState(false);
  const [hasilGeo, setHasilGeo] = useState(null);

  const muat = useCallback(() => {
    setMemuat(true);
    return api
      .polsek()
      .then((fc) =>
        setDaftar(
          fc.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek, punyaPoligon: !!f.geometry }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        )
      )
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [setPesan]);

  useEffect(() => {
    muat();
  }, [muat]);

  async function tambah(e) {
    e.preventDefault();
    setPesan(null);
    const body = { nama_polsek: baru.nama_polsek.trim() };
    if (baru.nama_wilayah_resmi.trim()) body.nama_wilayah_resmi = baru.nama_wilayah_resmi.trim();
    try {
      const r = await api.tambahPolsek(token, body);
      setPesan({ tipe: 'success', teks: `Polsek ${r.nama_polsek} ditambahkan. Unggah poligonnya agar tampil di peta.` });
      setBaru({ nama_polsek: '', nama_wilayah_resmi: '' });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menambah Polsek: ') });
    }
  }

  async function simpanNama(p) {
    setPesan(null);
    const nama = ubahNama.trim();
    // Nama di layar sudah dirapikan (mis. "Baleendah"); jangan kirim kalau teksnya tidak diubah
    // supaya nama asli di database tidak ikut berubah.
    if (!nama || nama === p.nama) {
      setUbahId(null);
      return;
    }
    try {
      await api.ubahPolsek(token, p.id, { nama_polsek: nama });
      setPesan({ tipe: 'success', teks: `Nama Polsek diganti menjadi ${nama}.` });
      setUbahId(null);
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal mengubah nama: ') });
    }
  }

  async function hapus(p) {
    if (!window.confirm(`Hapus Polsek "${p.nama}"?\n\nHanya bisa jika tidak punya data kasus. Tindakan ini tidak bisa dibatalkan.`)) return;
    setPesan(null);
    try {
      await api.hapusPolsek(token, p.id);
      setPesan({ tipe: 'success', teks: `Polsek ${p.nama} dihapus.` });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menghapus Polsek: ') });
    }
  }

  async function unggah(hanyaPeriksa) {
    if (!berkas) {
      setHasilGeo({ tipe: 'gagal', pesan: 'Pilih berkas GeoJSON dulu.', detail: [] });
      return;
    }
    const f = new FormData();
    f.append('file', berkas);
    f.append('dry_run', String(hanyaPeriksa));
    setSedangUnggah(true);
    setHasilGeo(null);
    try {
      const r = await api.unggahGeojson(token, f);
      setHasilGeo({ tipe: 'ok', data: r, hanyaPeriksa });
      if (!hanyaPeriksa) muat();
    } catch (err) {
      setHasilGeo({ tipe: 'gagal', pesan: galat(err, ''), detail: err.detail || [] });
    } finally {
      setSedangUnggah(false);
    }
  }

  const tanpaPoligon = daftar.filter((p) => !p.punyaPoligon).length;

  return (
    <div className="row g-3">
      <div className="col-12 col-xl-7">
        <div className="card">
          <div className="card-body">
            <h2 className="h5">Daftar Polsek</h2>
            {tanpaPoligon > 0 && (
              <div className="small text-secondary mb-2">{tanpaPoligon} Polsek belum punya poligon wilayah (tidak tampil di peta).</div>
            )}
            <div className="table-responsive">
              <table className="table table-sm table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>Polsek</th>
                    <th>Poligon</th>
                    <th className="text-end">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {memuat && <tr><td colSpan="3" className="text-center text-secondary py-3">Memuat…</td></tr>}
                  {!memuat && daftar.map((p) => {
                    const diUbah = ubahId === p.id;
                    return (
                      <tr key={p.id}>
                        <td>
                          {diUbah ? (
                            <input className="form-control form-control-sm" aria-label="Nama Polsek" maxLength={100}
                              value={ubahNama} onChange={(e) => setUbahNama(e.target.value)} />
                          ) : p.nama}
                        </td>
                        <td>{p.punyaPoligon ? 'Ada' : <span className="text-secondary">Belum</span>}</td>
                        <td className="text-end">
                          <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                            {diUbah ? (
                              <>
                                <button type="button" className="btn btn-primary btn-sm" onClick={() => simpanNama(p)}>Simpan</button>
                                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setUbahId(null)}>Batal</button>
                              </>
                            ) : (
                              <>
                                <button type="button" className="btn btn-outline-primary btn-sm"
                                  onClick={() => { setUbahId(p.id); setUbahNama(p.nama); }}>Ubah nama</button>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => hapus(p)}>Hapus</button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="col-12 col-xl-5 d-flex flex-column gap-3">
        <form className="card card-body" onSubmit={tambah}>
          <h2 className="h5">Tambah Polsek</h2>
          <div className="mb-2">
            <label className="form-label small fw-semibold" htmlFor="p-nama">Nama Polsek</label>
            <input id="p-nama" className="form-control form-control-sm" required minLength={3} maxLength={100}
              placeholder="mis. Soreang" value={baru.nama_polsek} onChange={(e) => setBaru({ ...baru, nama_polsek: e.target.value })} />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-semibold" htmlFor="p-wil">Nama kecamatan (opsional)</label>
            <input id="p-wil" className="form-control form-control-sm" maxLength={100}
              value={baru.nama_wilayah_resmi} onChange={(e) => setBaru({ ...baru, nama_wilayah_resmi: e.target.value })} />
          </div>
          <button className="btn btn-primary btn-sm" type="submit">Tambah Polsek</button>
        </form>

        <div className="card">
          <div className="card-body">
            <h2 className="h5">Unggah poligon wilayah</h2>
            <p className="small text-secondary">
              GeoJSON <code>FeatureCollection</code> (WGS 84). Tiap fitur: <code>properties.id_polsek</code> atau{' '}
              <code>nama_polsek</code> + geometri Polygon/MultiPolygon. Boleh sebagian Polsek saja. Server memeriksa geometri,
              luas, dan tumpang tindih; kalau ada yang salah, tidak ada yang disimpan.
            </p>
            <input type="file" accept=".geojson,.json,application/geo+json,application/json" className="form-control form-control-sm mb-2"
              onChange={(e) => { setBerkas(e.target.files[0] || null); setHasilGeo(null); }} />
            <div className="d-grid gap-2">
              <button type="button" className="btn btn-outline-primary btn-sm" disabled={sedangUnggah} onClick={() => unggah(true)}>
                1. Periksa dulu (tidak menyimpan)
              </button>
              <button type="button" className="btn btn-primary btn-sm" disabled={sedangUnggah}
                onClick={() => { if (window.confirm('Poligon Polsek yang ada di berkas akan DIGANTI. Lanjutkan?')) unggah(false); }}>
                2. Simpan poligon
              </button>
            </div>
            {sedangUnggah && <div className="small text-secondary mt-2">Memproses berkas…</div>}

            {hasilGeo && hasilGeo.tipe === 'ok' && (
              <div className="alert alert-success mt-3 mb-0 py-2 small" role="status">
                <strong>{hasilGeo.hanyaPeriksa ? 'Berkas valid (belum disimpan).' : 'Poligon disimpan.'}</strong>
                <div>
                  {hasilGeo.data.fitur_dibaca} fitur dibaca · {hasilGeo.data.polsek_diperbarui.length} Polsek:{' '}
                  {hasilGeo.data.polsek_diperbarui.map((x) => x.nama_polsek).join(', ')}
                </div>
                {hasilGeo.data.diperbaiki_otomatis.length > 0 && (
                  <div>Geometri diperbaiki otomatis: {hasilGeo.data.diperbaiki_otomatis.join(', ')}</div>
                )}
                {hasilGeo.data.peringatan.length > 0 && (
                  <ul className="mb-0 mt-1 ps-3">{hasilGeo.data.peringatan.map((w, i) => <li key={i}>{w}</li>)}</ul>
                )}
              </div>
            )}
            {hasilGeo && hasilGeo.tipe === 'gagal' && (
              <div className="alert alert-danger mt-3 mb-0 py-2 small" role="alert">
                <strong>{hasilGeo.pesan || 'Unggah gagal.'}</strong>
                {hasilGeo.detail.length > 0 && (
                  <ul className="mb-0 mt-1 ps-3">{hasilGeo.detail.map((d, i) => <li key={i}>{d}</li>)}</ul>
                )}
                <div className="mt-1">Tidak ada poligon yang diubah.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Tab Jenis kejahatan
function TabJenis({ token, setPesan }) {
  const [daftar, setDaftar] = useState([]);
  const [memuat, setMemuat] = useState(true);
  const [baru, setBaru] = useState({ kode_jenis: '', nama_jenis: '' });
  const [ubahId, setUbahId] = useState(null);
  const [ubahNama, setUbahNama] = useState('');

  const muat = useCallback(() => {
    setMemuat(true);
    return api
      .jenis()
      .then((r) => setDaftar(r.data))
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [setPesan]);

  useEffect(() => {
    muat();
  }, [muat]);

  async function tambah(e) {
    e.preventDefault();
    setPesan(null);
    try {
      await api.tambahJenis(token, { kode_jenis: baru.kode_jenis.trim(), nama_jenis: baru.nama_jenis.trim() });
      setPesan({ tipe: 'success', teks: `Jenis ${baru.nama_jenis.trim()} ditambahkan. Isi jumlahnya lewat Tambah Data atau Titik Kejadian (tidak lewat impor CSV rekap).` });
      setBaru({ kode_jenis: '', nama_jenis: '' });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menambah jenis: ') });
    }
  }

  async function simpanNama(j) {
    setPesan(null);
    const nama = ubahNama.trim();
    if (!nama || nama === j.nama_jenis) {
      setUbahId(null);
      return;
    }
    try {
      await api.ubahJenis(token, j.id_jenis, { nama_jenis: nama });
      setPesan({ tipe: 'success', teks: 'Nama jenis diperbarui.' });
      setUbahId(null);
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal mengubah jenis: ') });
    }
  }

  async function hapus(j) {
    if (!window.confirm(`Hapus jenis "${j.nama_jenis}"?\n\nTindakan ini tidak bisa dibatalkan.`)) return;
    setPesan(null);
    try {
      await api.hapusJenis(token, j.id_jenis);
      setPesan({ tipe: 'success', teks: `Jenis ${j.nama_jenis} dihapus.` });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menghapus jenis: ') });
    }
  }

  return (
    <div className="row g-3">
      <div className="col-12 col-xl-8">
        <div className="card">
          <div className="card-body">
            <h2 className="h5">Jenis kejahatan</h2>
            <p className="small text-secondary">
              Jenis baku (dipakai impor CSV rekap) tidak bisa dihapus atau diganti kodenya; namanya boleh diubah.
            </p>
            <div className="table-responsive">
              <table className="table table-sm table-hover align-middle mb-0">
                <thead>
                  <tr>
                    <th>Kode</th>
                    <th>Nama</th>
                    <th className="text-end">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {memuat && <tr><td colSpan="3" className="text-center text-secondary py-3">Memuat…</td></tr>}
                  {!memuat && daftar.map((j) => {
                    const diUbah = ubahId === j.id_jenis;
                    return (
                      <tr key={j.id_jenis}>
                        <td><code>{j.kode_jenis}</code></td>
                        <td>
                          {diUbah ? (
                            <input className="form-control form-control-sm" aria-label="Nama jenis" maxLength={100}
                              value={ubahNama} onChange={(e) => setUbahNama(e.target.value)} />
                          ) : j.nama_jenis}
                        </td>
                        <td className="text-end">
                          <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                            {diUbah ? (
                              <>
                                <button type="button" className="btn btn-primary btn-sm" onClick={() => simpanNama(j)}>Simpan</button>
                                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setUbahId(null)}>Batal</button>
                              </>
                            ) : (
                              <>
                                <button type="button" className="btn btn-outline-primary btn-sm"
                                  onClick={() => { setUbahId(j.id_jenis); setUbahNama(j.nama_jenis); }}>Ubah nama</button>
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => hapus(j)}>Hapus</button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div className="col-12 col-xl-4">
        <form className="card card-body" onSubmit={tambah}>
          <h2 className="h5">Tambah jenis</h2>
          <div className="mb-2">
            <label className="form-label small fw-semibold" htmlFor="j-kode">Kode (huruf besar, angka, _)</label>
            <input id="j-kode" className="form-control form-control-sm" required pattern="[A-Z0-9_]{2,30}"
              title="2-30 karakter: huruf besar, angka, atau _" placeholder="mis. NARKOBA" autoComplete="off"
              value={baru.kode_jenis} onChange={(e) => setBaru({ ...baru, kode_jenis: e.target.value.toUpperCase() })} />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-semibold" htmlFor="j-nama">Nama jenis</label>
            <input id="j-nama" className="form-control form-control-sm" required minLength={2} maxLength={100}
              value={baru.nama_jenis} onChange={(e) => setBaru({ ...baru, nama_jenis: e.target.value })} />
          </div>
          <button className="btn btn-primary btn-sm" type="submit">Tambah jenis</button>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- Tab Catatan tahun
// Catatan per tahun data ditampilkan sebagai peringatan di Peta dan Dashboard (mis. "Data 2025 adalah SIMULASI").
// Hapus catatannya setelah data tahun itu diganti dengan data resmi.
function TabCatatan({ token, setPesan }) {
  const [tahunAda, setTahunAda] = useState([]);
  const [catatan, setCatatan] = useState({});
  const [memuat, setMemuat] = useState(true);
  const [form, setForm] = useState({ tahun: '', catatan: '' });

  const muat = useCallback(() => {
    setMemuat(true);
    return api
      .tahun()
      .then((r) => {
        setTahunAda(r.data);
        setCatatan(r.catatan || {});
      })
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [setPesan]);

  useEffect(() => {
    muat();
  }, [muat]);

  const semuaTahun = [...new Set([...tahunAda.map(String), ...Object.keys(catatan)])].sort();

  async function simpan(e) {
    e.preventDefault();
    setPesan(null);
    try {
      await api.aturCatatanTahun(token, Number(form.tahun), form.catatan.trim());
      setPesan({ tipe: 'success', teks: `Catatan tahun ${form.tahun} disimpan.` });
      setForm({ tahun: '', catatan: '' });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menyimpan catatan: ') });
    }
  }

  async function hapus(tahun) {
    if (!window.confirm(`Hapus catatan tahun ${tahun}?\n\nPeringatannya tidak akan tampil lagi di Peta dan Dashboard.`)) return;
    setPesan(null);
    try {
      await api.hapusCatatanTahun(token, Number(tahun));
      setPesan({ tipe: 'success', teks: `Catatan tahun ${tahun} dihapus.` });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menghapus catatan: ') });
    }
  }

  return (
    <div className="row g-3">
      <div className="col-12 col-xl-7">
        <div className="card">
          <div className="card-body">
            <h2 className="h5">Catatan per tahun</h2>
            <p className="small text-secondary">
              Dipakai untuk memberi tahu pengunjung bahwa data tahun tertentu belum resmi (mis. simulasi) atau baru sebagian.
            </p>
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-0">
                <thead>
                  <tr>
                    <th>Tahun</th>
                    <th>Catatan</th>
                    <th className="text-end">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {memuat && <tr><td colSpan="3" className="text-center text-secondary py-3">Memuat…</td></tr>}
                  {!memuat && semuaTahun.map((t) => (
                    <tr key={t}>
                      <td>{t}{!tahunAda.map(String).includes(t) && <span className="small text-secondary"> (belum ada data)</span>}</td>
                      <td>{catatan[t] || <span className="text-secondary">—</span>}</td>
                      <td className="text-end">
                        <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                          <button type="button" className="btn btn-outline-primary btn-sm"
                            onClick={() => setForm({ tahun: t, catatan: catatan[t] || '' })}>Ubah</button>
                          {catatan[t] && (
                            <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => hapus(t)}>Hapus</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      <div className="col-12 col-xl-5">
        <form className="card card-body" onSubmit={simpan}>
          <h2 className="h5">Atur catatan</h2>
          <div className="mb-2">
            <label className="form-label small fw-semibold" htmlFor="c-tahun">Tahun</label>
            <input id="c-tahun" type="number" className="form-control form-control-sm" required min="2000" max="2100"
              value={form.tahun} onChange={(e) => setForm({ ...form, tahun: e.target.value })} />
          </div>
          <div className="mb-3">
            <label className="form-label small fw-semibold" htmlFor="c-teks">Catatan (3-500 karakter)</label>
            <textarea id="c-teks" rows={3} className="form-control form-control-sm" required minLength={3} maxLength={500}
              placeholder="mis. Data simulasi untuk pengembangan, bukan data resmi."
              value={form.catatan} onChange={(e) => setForm({ ...form, catatan: e.target.value })} />
          </div>
          <button className="btn btn-primary btn-sm" type="submit">Simpan catatan</button>
        </form>
      </div>
    </div>
  );
}

export default function MasterDataPage() {
  const { sesi } = useAuth();
  const [tab, setTab] = useState('polsek');
  const [pesan, setPesan] = useState(null);

  if (sesi.pengguna.peran !== 'admin') {
    return <div className="alert alert-warning">Halaman ini khusus admin.</div>;
  }

  return (
    <>
      <h1 className="h3 mb-3">Master Data</h1>
      <Pesan pesan={pesan} tutup={() => setPesan(null)} />
      <ul className="nav nav-tabs mb-3">
        {[['polsek', 'Polsek & poligon'], ['jenis', 'Jenis kejahatan'], ['catatan', 'Catatan tahun']].map(([k, teks]) => (
          <li className="nav-item" key={k}>
            <button type="button" className={`nav-link${tab === k ? ' active' : ''}`} onClick={() => { setTab(k); setPesan(null); }}>
              {teks}
            </button>
          </li>
        ))}
      </ul>
      {tab === 'polsek' && <TabPolsek token={sesi.token} setPesan={setPesan} />}
      {tab === 'jenis' && <TabJenis token={sesi.token} setPesan={setPesan} />}
      {tab === 'catatan' && <TabCatatan token={sesi.token} setPesan={setPesan} />}
    </>
  );
}
