import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Halaman Tambah Data Kasus (admin/operator), terpisah dari tabel Kelola Data.
// Setelah berhasil menyimpan, kembali ke tabel dengan pesan sukses.
export default function TambahKasusPage() {
  const { sesi } = useAuth();
  const navigate = useNavigate();
  const lokasi = useLocation();

  const [daftarJenis, setDaftarJenis] = useState([]);
  const [daftarPolsek, setDaftarPolsek] = useState([]);
  const [form, setForm] = useState({
    id_polsek: '',
    id_jenis: '',
    tahun: lokasi.state?.tahun ? String(lokasi.state.tahun) : '',
    jumlah: '',
  });
  const [memuat, setMemuat] = useState(true);
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [galat, setGalat] = useState('');
  const [sukses, setSukses] = useState('');

  // Isi pilihan dropdown; tahun awal = tahun terbaru kalau belum ada dari tabel.
  useEffect(() => {
    Promise.all([api.tahun(), api.jenis(), api.polsek()])
      .then(([t, j, p]) => {
        setDaftarJenis(j.data);
        setDaftarPolsek(
          p.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        );
        setForm((f) => ({ ...f, tahun: f.tahun || String(t.terbaru) }));
      })
      .catch((e) => setGalat(e.message))
      .finally(() => setMemuat(false));
  }, []);

  function pesanGalat(e) {
    if (e.status === 403) return 'Peran kamu tidak diizinkan menambah data.';
    if (e.status === 409)
      return 'Data untuk Polsek, jenis, dan tahun itu sudah ada. Buka Kelola Data lalu pakai tombol Ubah untuk mengganti jumlahnya.';
    return `Gagal menambah data: ${e.message}`;
  }

  // lagi = true: tetap di halaman ini untuk memasukkan data berikutnya.
  async function simpan(e, lagi) {
    e.preventDefault();
    setSedangSimpan(true);
    setGalat('');
    setSukses('');
    try {
      await api.tambahKasus(sesi.token, {
        id_polsek: Number(form.id_polsek),
        id_jenis: Number(form.id_jenis),
        tahun: Number(form.tahun),
        jumlah: Number(form.jumlah),
      });
      const teks = 'Data berhasil ditambahkan. Warna zona di peta ikut diperbarui.';
      if (lagi) {
        setSukses(teks);
        setForm({ ...form, jumlah: '' });
      } else {
        navigate('/admin', { replace: true, state: { pesan: teks } });
      }
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
        <h1 className="h3">Tambah data kasus</h1>
        <p className="text-secondary">
          Masukkan jumlah kasus satu jenis kejahatan untuk satu Polsek pada satu tahun.
        </p>

        {sukses && (
          <div className="alert alert-success py-2" role="status">
            {sukses}
          </div>
        )}
        {galat && (
          <div className="alert alert-danger py-2" role="alert">
            {galat}
          </div>
        )}

        <form className="card card-body" onSubmit={(e) => simpan(e, false)}>
          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="t-polsek">Wilayah (Polsek)</label>
            <select
              id="t-polsek"
              className="form-select"
              required
              disabled={memuat}
              value={form.id_polsek}
              onChange={(e) => setForm({ ...form, id_polsek: e.target.value })}
            >
              <option value="">{memuat ? 'Memuat…' : 'Pilih Polsek…'}</option>
              {daftarPolsek.map((p) => (
                <option key={p.id} value={p.id}>{p.nama}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="t-jenis">Jenis kejahatan</label>
            <select
              id="t-jenis"
              className="form-select"
              required
              disabled={memuat}
              value={form.id_jenis}
              onChange={(e) => setForm({ ...form, id_jenis: e.target.value })}
            >
              <option value="">{memuat ? 'Memuat…' : 'Pilih jenis…'}</option>
              {daftarJenis.map((j) => (
                <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>
              ))}
            </select>
          </div>

          <div className="row g-3 mb-3">
            <div className="col-6">
              <label className="form-label fw-semibold" htmlFor="t-tahun">Tahun</label>
              <input
                id="t-tahun"
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
              <label className="form-label fw-semibold" htmlFor="t-jumlah">Jumlah kasus</label>
              <input
                id="t-jumlah"
                type="number"
                className="form-control"
                min="0"
                required
                value={form.jumlah}
                onChange={(e) => setForm({ ...form, jumlah: e.target.value })}
              />
            </div>
          </div>

          <div className="d-flex flex-column flex-sm-row gap-2">
            <button className="btn btn-primary" type="submit" disabled={sedangSimpan || memuat}>
              {sedangSimpan ? 'Menyimpan…' : 'Simpan'}
            </button>
            <button
              className="btn btn-outline-primary"
              type="button"
              disabled={sedangSimpan || memuat}
              onClick={(e) => {
                // Pakai validasi bawaan form sebelum menyimpan.
                const f = e.currentTarget.form;
                if (f.reportValidity()) simpan(e, true);
              }}
            >
              Simpan dan tambah lagi
            </button>
            <Link className="btn btn-outline-secondary" to="/admin">Batal</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
