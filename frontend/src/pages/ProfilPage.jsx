import { useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Profil (admin/operator): lihat identitas sendiri dan ubah password.
// Endpoint: POST /api/auth/ubah-password (password lama salah -> 400).
export default function ProfilPage() {
  const { sesi } = useAuth();
  const p = sesi.pengguna;
  const [form, setForm] = useState({ lama: '', baru: '', ulang: '' });
  const [sedang, setSedang] = useState(false);
  const [pesan, setPesan] = useState(null); // { tipe, teks }

  async function simpan(e) {
    e.preventDefault();
    setPesan(null);
    if (form.baru.length < 8) return setPesan({ tipe: 'danger', teks: 'Password baru minimal 8 karakter.' });
    if (form.baru !== form.ulang) return setPesan({ tipe: 'danger', teks: 'Konfirmasi password tidak sama.' });
    if (form.baru === form.lama) return setPesan({ tipe: 'danger', teks: 'Password baru harus berbeda dari yang lama.' });
    setSedang(true);
    try {
      await api.ubahPassword(sesi.token, form.lama, form.baru);
      setForm({ lama: '', baru: '', ulang: '' });
      setPesan({ tipe: 'success', teks: 'Password berhasil diubah.' });
    } catch (err) {
      setPesan({
        tipe: 'danger',
        teks: err.status === 400 ? err.message : `Gagal mengubah password: ${err.message}`,
      });
    } finally {
      setSedang(false);
    }
  }

  return (
    <div className="row g-3 justify-content-center">
      <div className="col-12 col-lg-5">
        <div className="card h-100">
          <div className="card-body">
            <h1 className="h5 mb-3">Identitas</h1>
            <div className="text-secondary small">Username</div>
            <div className="fs-5 fw-bold mb-3">{p.username}</div>
            <div className="text-secondary small">Peran</div>
            <div className="fs-5 fw-bold mb-3 text-capitalize">{p.peran}</div>
            <div className="text-secondary small">ID pengguna</div>
            <div className="fw-bold">{p.id_pengguna}</div>
          </div>
        </div>
      </div>

      <div className="col-12 col-lg-5">
        <form className="card card-body" onSubmit={simpan}>
          <h2 className="h5 mb-3">Ubah password</h2>
          {pesan && <div className={`alert alert-${pesan.tipe} py-2`} role="alert">{pesan.teks}</div>}
          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="p-lama">Password lama</label>
            <input id="p-lama" type="password" className="form-control" required autoComplete="current-password"
              value={form.lama} onChange={(e) => setForm({ ...form, lama: e.target.value })} />
          </div>
          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="p-baru">Password baru (min. 8 karakter)</label>
            <input id="p-baru" type="password" className="form-control" required minLength={8} maxLength={72} autoComplete="new-password"
              value={form.baru} onChange={(e) => setForm({ ...form, baru: e.target.value })} />
          </div>
          <div className="mb-3">
            <label className="form-label fw-semibold" htmlFor="p-ulang">Ulangi password baru</label>
            <input id="p-ulang" type="password" className="form-control" required maxLength={72} autoComplete="new-password"
              value={form.ulang} onChange={(e) => setForm({ ...form, ulang: e.target.value })} />
          </div>
          <button className="btn btn-primary" type="submit" disabled={sedang}>
            {sedang ? 'Menyimpan…' : 'Simpan password'}
          </button>
        </form>
      </div>
    </div>
  );
}
