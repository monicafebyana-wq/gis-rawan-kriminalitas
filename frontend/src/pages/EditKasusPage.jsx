import { useEffect, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Halaman Ubah Data Kasus: ubah Polsek, jenis kejahatan, tahun, dan jumlah.
// Data awal dikirim dari tabel Kelola Data lewat state navigasi (baris yang diklik "Ubah").
export default function EditKasusPage() {
  const { sesi } = useAuth();
  const navigate = useNavigate();
  const lokasi = useLocation();
  const kasus = lokasi.state?.kasus;

  const [daftarJenis, setDaftarJenis] = useState([]);
  const [daftarPolsek, setDaftarPolsek] = useState([]);
  const [form, setForm] = useState({
    id_polsek: String(kasus?.id_polsek ?? ''),
    id_jenis: String(kasus?.id_jenis ?? ''),
    tahun: String(kasus?.tahun ?? ''),
    jumlah: String(kasus?.jumlah ?? ''),
  });
  const [memuat, setMemuat] = useState(true);
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [galat, setGalat] = useState('');

  useEffect(() => {
    Promise.all([api.jenis(), api.polsek()])
      .then(([j, p]) => {
        setDaftarJenis(j.data);
        setDaftarPolsek(
          p.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        );
      })
      .catch((e) => setGalat(e.message))
      .finally(() => setMemuat(false));
  }, []);

  // Dibuka langsung tanpa memilih baris (mis. setelah refresh): kembali ke tabel.
  if (!kasus) return <Navigate to="/admin" replace />;

  function pesanGalat(e) {
    if (e.status === 403) return 'Peran kamu tidak diizinkan mengubah data.';
    if (e.status === 409) return 'Kombinasi Polsek, jenis, dan tahun itu sudah dipakai data kasus lain. Ubah salah satunya.';
    if (e.status === 404) return 'Data tidak ditemukan (mungkin sudah dihapus).';
    return `Gagal mengubah data: ${e.message}`;
  }

  async function simpan(e) {
    e.preventDefault();
    setGalat('');

    // Kirim hanya field yang berubah.
    const baru = {
      id_polsek: Number(form.id_polsek),
      id_jenis: Number(form.id_jenis),
      tahun: Number(form.tahun),
      jumlah: Number(form.jumlah),
    };
    const perubahan = {};
    Object.keys(baru).forEach((k) => {
      if (baru[k] !== Number(kasus[k])) perubahan[k] = baru[k];
    });
    if (Object.keys(perubahan).length === 0) {
      setGalat('Belum ada yang diubah.');
      return;
    }

    setSedangSimpan(true);
    try {
      await api.ubahKasus(sesi.token, kasus.id_kasus, perubahan);
      navigate('/admin', { replace: true, state: { pesan: 'Data berhasil diubah. Warna zona di peta ikut diperbarui.' } });
    } catch (err) {
      setGalat(pesanGalat(err));
    } finally {
      setSedangSimpan(false);
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-12 col-md-8 col-lg-6 col-xl-5">
        <nav aria-label="breadcrumb" className="small mb-2">
          <Link to="/admin">← Kembali ke Kelola Data</Link>
        </nav>
        <h1 className="h3">Ubah data kasus</h1>
        <p className="text-secondary">
          Data saat ini: {kasus.nama_polsek} – {kasus.nama_jenis} ({kasus.tahun}), jumlah {kasus.jumlah}.
        </p>

        {galat && <div className="alert alert-danger py-2" role="alert">{galat}</div>}

        <form className="card card-body" onSubmit={simpan}>
          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="e-polsek">Wilayah (Polsek)</label>
            <select id="e-polsek" className="form-select" required disabled={memuat} value={form.id_polsek}
              onChange={(e) => setForm({ ...form, id_polsek: e.target.value })}>
              <option value="">{memuat ? 'Memuat…' : 'Pilih Polsek…'}</option>
              {daftarPolsek.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
            </select>
          </div>

          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="e-jenis">Jenis kejahatan</label>
            <select id="e-jenis" className="form-select" required disabled={memuat} value={form.id_jenis}
              onChange={(e) => setForm({ ...form, id_jenis: e.target.value })}>
              <option value="">{memuat ? 'Memuat…' : 'Pilih jenis…'}</option>
              {daftarJenis.map((j) => <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>)}
            </select>
          </div>

          <div className="row g-3 mb-3">
            <div className="col-6">
              <label className="form-label fw-semibold" htmlFor="e-tahun">Tahun</label>
              <input id="e-tahun" type="number" className="form-control" min="2000" max="2100" required
                value={form.tahun} onChange={(e) => setForm({ ...form, tahun: e.target.value })} />
            </div>
            <div className="col-6">
              <label className="form-label fw-semibold" htmlFor="e-jumlah">Jumlah kasus</label>
              <input id="e-jumlah" type="number" className="form-control" min="0" required
                value={form.jumlah} onChange={(e) => setForm({ ...form, jumlah: e.target.value })} />
            </div>
          </div>

          <div className="d-flex flex-column flex-sm-row gap-2">
            <button className="btn btn-primary" type="submit" disabled={sedangSimpan || memuat}>
              {sedangSimpan ? 'Menyimpan…' : 'Simpan perubahan'}
            </button>
            <Link className="btn btn-outline-secondary" to="/admin">Batal</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
