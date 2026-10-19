import { useState } from 'react';
import { Link } from 'react-router-dom';

// Halaman login admin/operator.
// TODO task 32: panggil api.login(), simpan token, arahkan ke /admin.
export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  function kirim(e) {
    e.preventDefault();
    // Belum terhubung ke API (task 32).
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

            <label className="form-label fw-semibold" htmlFor="l-user">Nama pengguna</label>
            <input
              id="l-user"
              className="form-control mb-3"
              placeholder="contoh: admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <label className="form-label fw-semibold" htmlFor="l-pass">Kata sandi</label>
            <input
              id="l-pass"
              type="password"
              className="form-control mb-3"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <button className="btn btn-primary w-100" type="submit">Masuk</button>
            <div className="text-center mt-3">
              <Link to="/">← Kembali ke peta</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
