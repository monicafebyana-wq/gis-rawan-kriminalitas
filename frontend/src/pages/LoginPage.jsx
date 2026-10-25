import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

// Halaman login admin/operator. Berhasil -> simpan sesi -> halaman Kelola Data.
export default function LoginPage() {
  const { sesi, login } = useAuth();
  const navigate = useNavigate();
  const lokasi = useLocation();
  // Setelah mendaftar, nama pengguna dan pesan sukses dikirim lewat state rute.
  const [username, setUsername] = useState(lokasi.state?.username || '');
  const [password, setPassword] = useState('');
  const [galat, setGalat] = useState('');
  const [proses, setProses] = useState(false);

  if (sesi) return <Navigate to="/admin" replace />;

  async function kirim(e) {
    e.preventDefault();
    setGalat('');
    setProses(true);
    try {
      await login(username.trim(), password);
      navigate(lokasi.state?.dari || '/admin', { replace: true });
    } catch (err) {
      setGalat(
        err.status === 401 ? 'Nama pengguna atau kata sandi salah. Coba lagi.' : err.message
      );
      setProses(false);
    }
  }

  return (
    <div className="row justify-content-center py-4">
      <div className="col-12 col-sm-8 col-md-6 col-lg-4">
        <div className="card">
          <form className="card-body" onSubmit={kirim}>
            <h1 className="h4 text-center">Masuk Admin</h1>
            <p className="text-secondary text-center small">
              Khusus petugas pengelola data. Pengunjung biasa tidak perlu masuk.
            </p>

            {lokasi.state?.pesan && (
              <div className="alert alert-success py-2" role="status">
                {lokasi.state.pesan}
              </div>
            )}

            {galat && (
              <div className="alert alert-danger py-2" role="alert">
                {galat}
              </div>
            )}

            <label className="form-label fw-semibold" htmlFor="l-user">Nama pengguna</label>
            <input
              id="l-user"
              className="form-control mb-3"
              placeholder="contoh: admin"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            <label className="form-label fw-semibold" htmlFor="l-pass">Kata sandi</label>
            <input
              id="l-pass"
              type="password"
              className="form-control mb-3"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <button className="btn btn-primary w-100" type="submit" disabled={proses}>
              {proses ? 'Memeriksa…' : 'Masuk'}
            </button>
            <div className="text-center mt-3">
              Belum punya akun? <Link to="/daftar">Daftar</Link>
            </div>
            <div className="text-center mt-2">
              <Link to="/">← Kembali ke dashboard</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}