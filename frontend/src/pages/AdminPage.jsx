import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Halaman Kelola Data (admin/operator): tabel kasus, tambah, ubah, hapus, dan impor rekap CSV.
// Hak akses: operator boleh tambah/ubah/impor; hanya admin yang boleh hapus.
const BATAS = 20; // baris per halaman

export default function AdminPage() {
  const { sesi, logout } = useAuth();
  const token = sesi.token;
  const adalahAdmin = sesi.pengguna.peran === 'admin';

  // Pilihan untuk dropdown
  const [daftarTahun, setDaftarTahun] = useState([]);
  const [daftarJenis, setDaftarJenis] = useState([]);
  const [daftarPolsek, setDaftarPolsek] = useState([]);
  const [tahunBaru, setTahunBaru] = useState('');

  // Tabel
  const [filter, setFilter] = useState({ tahun: '', polsek: '', jenis: '' });
  const [halaman, setHalaman] = useState(1);
  const [hasil, setHasil] = useState(null); // { data, total_data }
  const [memuat, setMemuat] = useState(false);
  const [versi, setVersi] = useState(0); // naikkan untuk memuat ulang tabel
  const [pesan, setPesan] = useState(null); // { tipe: 'success'|'danger', teks }

  // Form tambah & ubah
  const [formBuka, setFormBuka] = useState(false);
  const [form, setForm] = useState({ id_polsek: '', id_jenis: '', tahun: '', jumlah: '' });
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [ubahId, setUbahId] = useState(null);
  const [ubahJumlah, setUbahJumlah] = useState('');

  // Impor CSV
  const [berkas, setBerkas] = useState(null);
  const [tahunImpor, setTahunImpor] = useState('');
  const [mode, setMode] = useState('timpa');
  const [sedangImpor, setSedangImpor] = useState(false);
  const [hasilImpor, setHasilImpor] = useState(null);

  const muatUlang = () => setVersi((v) => v + 1);

  // Isi pilihan dropdown sekali di awal (dan saat data tahun berubah lewat muatTahun).
  const muatTahun = useCallback(() => {
    return api.tahun().then((t) => {
      setDaftarTahun(t.data);
      return t.terbaru;
    });
  }, []);

  useEffect(() => {
    Promise.all([muatTahun(), api.jenis(), api.polsek()])
      .then(([terbaru, j, p]) => {
        setDaftarJenis(j.data);
        setDaftarPolsek(
          p.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        );
        setFilter((f) => ({ ...f, tahun: String(terbaru) }));
        setTahunBaru(String(terbaru));
        setTahunImpor(String(terbaru));
      })
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }));
  }, [muatTahun]);

  // Ambil data tabel setiap filter / halaman berubah.
  useEffect(() => {
    if (!filter.tahun) return;
    setMemuat(true);
    api
      .kasus({ ...filter, page: halaman, limit: BATAS })
      .then((r) => {
        // Halaman terakhir baru saja kosong (mis. setelah menghapus): mundur satu halaman.
        if (r.data.length === 0 && halaman > 1) setHalaman(halaman - 1);
        else setHasil(r);
      })
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [filter, halaman, versi]);

  function ubahFilter(kunci, nilai) {
    setFilter({ ...filter, [kunci]: nilai });
    setHalaman(1);
  }

  function pesanGalat(e, awalan) {
    if (e.status === 403) return 'Peran kamu tidak diizinkan melakukan ini.';
    if (e.status === 409)
      return 'Data untuk Polsek, jenis, dan tahun itu sudah ada. Pakai tombol Ubah di tabel untuk mengganti jumlahnya.';
    return `${awalan}${e.message}`;
  }

  async function tambah(e) {
    e.preventDefault();
    setSedangSimpan(true);
    setPesan(null);
    try {
      await api.tambahKasus(token, {
        id_polsek: Number(form.id_polsek),
        id_jenis: Number(form.id_jenis),
        tahun: Number(form.tahun),
        jumlah: Number(form.jumlah),
      });
      setPesan({ tipe: 'success', teks: 'Data berhasil ditambahkan. Warna zona di peta ikut diperbarui.' });
      setForm({ ...form, jumlah: '' });
      await muatTahun();
      muatUlang();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: pesanGalat(err, 'Gagal menambah data: ') });
    } finally {
      setSedangSimpan(false);
    }
  }

  async function simpanUbah(k) {
    setPesan(null);
    try {
      await api.ubahKasus(token, k.id_kasus, Number(ubahJumlah));
      setPesan({ tipe: 'success', teks: `Jumlah ${k.nama_polsek} – ${k.nama_jenis} diubah jadi ${ubahJumlah}.` });
      setUbahId(null);
      muatUlang();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: pesanGalat(err, 'Gagal mengubah data: ') });
    }
  }

  async function hapus(k) {
    const yakin = window.confirm(
      `Hapus data ini?\n\n${k.nama_polsek} – ${k.nama_jenis} (${k.tahun}), jumlah ${k.jumlah}\n\nTindakan ini tidak bisa dibatalkan.`
    );
    if (!yakin) return;
    setPesan(null);
    try {
      await api.hapusKasus(token, k.id_kasus);
      setPesan({ tipe: 'success', teks: 'Data berhasil dihapus.' });
      muatUlang();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: pesanGalat(err, 'Gagal menghapus data: ') });
    }
  }

  async function impor(hanyaPeriksa) {
    if (!berkas) {
      setHasilImpor({ tipe: 'gagal', pesan: 'Pilih berkas CSV dulu.', detail: [] });
      return;
    }
    if (!hanyaPeriksa && mode === 'timpa') {
      const lanjut = window.confirm(
        `Semua data tahun ${tahunImpor} akan DIGANTI dengan isi berkas ini. Lanjutkan?`
      );
      if (!lanjut) return;
    }
    const f = new FormData();
    f.append('file', berkas);
    f.append('tahun', tahunImpor);
    f.append('mode', mode);
    f.append('dry_run', String(hanyaPeriksa));
    setSedangImpor(true);
    setHasilImpor(null);
    try {
      const r = await api.imporCsv(token, f);
      setHasilImpor({ tipe: 'ok', data: r, hanyaPeriksa });
      if (!hanyaPeriksa) {
        await muatTahun();
        muatUlang();
      }
    } catch (err) {
      setHasilImpor({ tipe: 'gagal', pesan: pesanGalat(err, ''), detail: err.detail || [] });
    } finally {
      setSedangImpor(false);
    }
  }

  const total = hasil ? hasil.total_data : 0;
  const jumlahHalaman = Math.max(1, Math.ceil(total / BATAS));

  return (
    <>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <div>
          <h1 className="h3 mb-0">Kelola Data Kasus</h1>
          <div className="small text-secondary">
            Masuk sebagai <strong>{sesi.pengguna.username}</strong> ({sesi.pengguna.peran})
            {!adalahAdmin && ' · boleh menambah dan mengubah, tidak boleh menghapus'}
          </div>
        </div>
        <button type="button" className="btn btn-outline-secondary btn-sm" onClick={logout}>
          Keluar
        </button>
      </div>

      {pesan && (
        <div className={`alert alert-${pesan.tipe} alert-dismissible py-2`} role="alert">
          {pesan.teks}
          <button type="button" className="btn-close" aria-label="Tutup" onClick={() => setPesan(null)} />
        </div>
      )}

      <div className="row g-3">
        {/* Tabel data */}
        <div className="col-12 col-xl-8">
          <div className="card">
            <div className="card-body">
              <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
                <h2 className="h5 mb-0">Data kasus</h2>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => {
                    setFormBuka(!formBuka);
                    setForm({ ...form, tahun: form.tahun || filter.tahun });
                  }}
                >
                  {formBuka ? 'Tutup form' : '+ Tambah data'}
                </button>
              </div>

              {formBuka && (
                <form className="border rounded p-3 mb-3 bg-light" onSubmit={tambah}>
                  <div className="row g-2">
                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-semibold" htmlFor="a-polsek">Wilayah (Polsek)</label>
                      <select
                        id="a-polsek"
                        className="form-select"
                        required
                        value={form.id_polsek}
                        onChange={(e) => setForm({ ...form, id_polsek: e.target.value })}
                      >
                        <option value="">Pilih Polsek…</option>
                        {daftarPolsek.map((p) => (
                          <option key={p.id} value={p.id}>{p.nama}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-semibold" htmlFor="a-jenis">Jenis kejahatan</label>
                      <select
                        id="a-jenis"
                        className="form-select"
                        required
                        value={form.id_jenis}
                        onChange={(e) => setForm({ ...form, id_jenis: e.target.value })}
                      >
                        <option value="">Pilih jenis…</option>
                        {daftarJenis.map((j) => (
                          <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>
                        ))}
                      </select>
                    </div>
                    <div className="col-6">
                      <label className="form-label small fw-semibold" htmlFor="a-tahun">Tahun</label>
                      <input
                        id="a-tahun"
                        type="number"
                        className="form-control"
                        min="2000"
                        max="2100"
                        required
                        value={form.tahun}
                        onChange={(e) => setForm({ ...form, tahun: e.target.value })}
                      />
                    </div>
                    <div className="col-6">
                      <label className="form-label small fw-semibold" htmlFor="a-jumlah">Jumlah kasus</label>
                      <input
                        id="a-jumlah"
                        type="number"
                        className="form-control"
                        min="0"
                        required
                        value={form.jumlah}
                        onChange={(e) => setForm({ ...form, jumlah: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="d-flex gap-2 mt-3">
                    <button className="btn btn-primary btn-sm" type="submit" disabled={sedangSimpan}>
                      {sedangSimpan ? 'Menyimpan…' : 'Simpan'}
                    </button>
                    <button className="btn btn-outline-secondary btn-sm" type="button" onClick={() => setFormBuka(false)}>
                      Batal
                    </button>
                  </div>
                </form>
              )}

              <div className="row g-2 mb-3">
                <div className="col-4 col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="t-tahun">Tahun</label>
                  <select id="t-tahun" className="form-select form-select-sm" value={filter.tahun} onChange={(e) => ubahFilter('tahun', e.target.value)}>
                    {daftarTahun.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div className="col-8 col-md-4">
                  <label className="form-label small fw-semibold" htmlFor="t-polsek">Polsek</label>
                  <select id="t-polsek" className="form-select form-select-sm" value={filter.polsek} onChange={(e) => ubahFilter('polsek', e.target.value)}>
                    <option value="">Semua</option>
                    {daftarPolsek.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
                  </select>
                </div>
                <div className="col-12 col-md-5">
                  <label className="form-label small fw-semibold" htmlFor="t-jenis">Jenis kejahatan</label>
                  <select id="t-jenis" className="form-select form-select-sm" value={filter.jenis} onChange={(e) => ubahFilter('jenis', e.target.value)}>
                    <option value="">Semua</option>
                    {daftarJenis.map((j) => <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>)}
                  </select>
                </div>
              </div>

              <div className="table-responsive">
                <table className="table table-sm table-hover align-middle mb-2 tabel-admin">
                  <thead>
                    <tr>
                      <th>Polsek</th>
                      <th>Jenis kejahatan</th>
                      <th className="d-none d-sm-table-cell">Tahun</th>
                      <th className="text-end">Jumlah</th>
                      <th className="text-end">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hasil && hasil.data.length === 0 && (
                      <tr><td colSpan="5" className="text-center text-secondary py-3">Tidak ada data yang cocok.</td></tr>
                    )}
                    {hasil && hasil.data.map((k) => (
                      <tr key={k.id_kasus}>
                        <td>{k.nama_polsek}</td>
                        <td>{k.nama_jenis}</td>
                        <td className="d-none d-sm-table-cell">{k.tahun}</td>
                        <td className="text-end kolom-jumlah">
                          {ubahId === k.id_kasus ? (
                            <input
                              type="number"
                              min="0"
                              className="form-control form-control-sm text-end"
                              aria-label="Jumlah baru"
                              value={ubahJumlah}
                              autoFocus
                              onChange={(e) => setUbahJumlah(e.target.value)}
                            />
                          ) : (
                            k.jumlah
                          )}
                        </td>
                        <td className="text-end">
                          <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                          {ubahId === k.id_kasus ? (
                            <>
                              <button type="button" className="btn btn-primary btn-sm" disabled={ubahJumlah === ''} onClick={() => simpanUbah(k)}>Simpan</button>
                              <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setUbahId(null)}>Batal</button>
                            </>
                          ) : (
                            <>
                              <button
                                type="button"
                                className="btn btn-outline-primary btn-sm"
                                onClick={() => { setUbahId(k.id_kasus); setUbahJumlah(String(k.jumlah)); }}
                              >
                                Ubah
                              </button>
                              {adalahAdmin && (
                                <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => hapus(k)}>Hapus</button>
                              )}
                            </>
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
                  {memuat ? 'Memuat…' : `${total} data · halaman ${halaman} dari ${jumlahHalaman}`}
                </div>
                <div className="btn-group btn-group-sm">
                  <button type="button" className="btn btn-outline-secondary" disabled={halaman <= 1} onClick={() => setHalaman(halaman - 1)}>‹ Sebelumnya</button>
                  <button type="button" className="btn btn-outline-secondary" disabled={halaman >= jumlahHalaman} onClick={() => setHalaman(halaman + 1)}>Berikutnya ›</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Impor CSV */}
        <div className="col-12 col-xl-4">
          <div className="card">
            <div className="card-body">
              <h2 className="h5">Impor rekap CSV</h2>
              <p className="small text-secondary">
                Unggah rekap kasus satu tahun (satu baris per Polsek, satu kolom per jenis kejahatan).
                Disarankan <strong>periksa dulu</strong> sebelum menyimpan.
              </p>

              <label className="form-label small fw-semibold" htmlFor="i-berkas">Berkas CSV (maks. 2 MB)</label>
              <input
                id="i-berkas"
                type="file"
                accept=".csv,text/csv"
                className="form-control form-control-sm mb-2"
                onChange={(e) => { setBerkas(e.target.files[0] || null); setHasilImpor(null); }}
              />

              <div className="row g-2 mb-2">
                <div className="col-5">
                  <label className="form-label small fw-semibold" htmlFor="i-tahun">Tahun</label>
                  <input id="i-tahun" type="number" min="2000" max="2100" className="form-control form-control-sm" value={tahunImpor} onChange={(e) => setTahunImpor(e.target.value)} />
                </div>
                <div className="col-7">
                  <label className="form-label small fw-semibold" htmlFor="i-mode">Cara menyimpan</label>
                  <select id="i-mode" className="form-select form-select-sm" value={mode} onChange={(e) => setMode(e.target.value)}>
                    <option value="timpa">Ganti semua data tahun ini</option>
                    <option value="tambah">Gabung (tambah / perbarui)</option>
                  </select>
                </div>
              </div>

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
                  <div>{hasilImpor.data.baris_valid} dari {hasilImpor.data.baris_dibaca} baris valid · total {hasilImpor.data.total_kasus} kasus (tahun {hasilImpor.data.tahun})</div>
                  {hasilImpor.data.peringatan.length > 0 && (
                    <ul className="mb-0 mt-1 ps-3">
                      {hasilImpor.data.peringatan.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  )}
                </div>
              )}
              {hasilImpor && hasilImpor.tipe === 'gagal' && (
                <div className="alert alert-danger mt-3 mb-0 py-2 small" role="alert">
                  <strong>{hasilImpor.pesan || 'Impor gagal.'}</strong>
                  {hasilImpor.detail.length > 0 && (
                    <ul className="mb-0 mt-1 ps-3">
                      {hasilImpor.detail.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
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
