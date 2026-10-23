import { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Halaman pendaftaran akun petugas. Berhasil -> diarahkan ke halaman Masuk.
export default function RegisterPage() {
  const { sesi } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [ulang, setUlang] = useState('');
  const [galat, setGalat] = useState('');
  const [proses, setProses] = useState(false);

  if (sesi) return <Navigate to="/admin" replace />;

  // Aturan ini usulan; samakan dengan aturan di backend.
  function periksa() {
    const nama = username.trim();
    if (!/^[A-Za-z0-9_.-]{3,50}$/.test(nama))
      return 'Nama pengguna 3–50 karakter: huruf, angka, titik, garis bawah, atau strip.';
    if (password.length < 8) return 'Kata sandi minimal 8 karakter.';
    if (new TextEncoder().encode(password).length > 72) return 'Kata sandi terlalu panjang (maksimal 72 karakter).';
    if (password !== ulang) return 'Kata sandi dan pengulangannya tidak sama.';
    return '';
  }

  async function kirim(e) {
    e.preventDefault();
    const masalah = periksa();
    if (masalah) return setGalat(masalah);
    setGalat('');
    setProses(true);
    try {
      await api.register(username.trim(), password);
      navigate('/login', {
        replace: true,
        state: { pesan: 'Akun berhasil dibuat. Silakan masuk.', username: username.trim() },
      });
    } catch (err) {
      if (err.status === 409) setGalat('Nama pengguna sudah dipakai. Coba nama lain.');
      else if ([404, 405, 501].includes(err.status))
        setGalat('Fitur pendaftaran belum tersedia di server. Hubungi admin untuk dibuatkan akun.');
      else setGalat(err.message);
      setProses(false);
    }
  }

  return (
    <div className="row justify-content-center py-4">
      <div className="col-12 col-sm-8 col-md-6 col-lg-4">
        <div className="card">
          <form className="card-body" onSubmit={kirim}>
            <h1 className="h4 text-center">Daftar Akun</h1>
            <p className="text-secondary text-center small">
              Untuk petugas pengelola data. Setelah daftar, silakan masuk.
            </p>

            {galat && <div className="alert alert-danger py-2" role="alert">{galat}</div>}

            <label className="form-label fw-semibold" htmlFor="r-user">Nama pengguna</label>
            <input
              id="r-user"
              className="form-control mb-3"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            <label className="form-label fw-semibold" htmlFor="r-pass">Kata sandi</label>
            <input
              id="r-pass"
              type="password"
              className="form-control"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <div className="form-text mb-3">Minimal 8 karakter.</div>

            <label className="form-label fw-semibold" htmlFor="r-ulang">Ulangi kata sandi</label>
            <input
              id="r-ulang"
              type="password"
              className="form-control mb-3"
              autoComplete="new-password"
              value={ulang}
              onChange={(e) => setUlang(e.target.value)}
              required
            />

            <button className="btn btn-primary w-100" type="submit" disabled={proses}>
              {proses ? 'Mendaftarkan…' : 'Daftar'}
            </button>
            <div className="text-center mt-3">
              Sudah punya akun? <Link to="/login">Masuk</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}