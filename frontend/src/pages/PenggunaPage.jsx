import { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Kelola Admin (khusus admin): daftar akun, tambah, ubah peran / reset password, hapus.
// Akun hanya bisa dibuat oleh admin lewat halaman ini.
// Endpoint: GET/POST /api/pengguna, PUT/DELETE /api/pengguna/{id}.
const PERAN = ['admin', 'operator'];

export default function PenggunaPage() {
  const { sesi } = useAuth();
  const token = sesi.token;
  const adalahAdmin = sesi.pengguna.peran === 'admin';

  const [daftar, setDaftar] = useState([]);
  const [memuat, setMemuat] = useState(true);
  const [pesan, setPesan] = useState(null);
  const [baru, setBaru] = useState({ username: '', password: '', peran: 'operator' });
  const [ubahId, setUbahId] = useState(null);
  const [ubah, setUbah] = useState({ peran: 'operator', password: '' });

  const muat = useCallback(() => {
    setMemuat(true);
    return api
      .pengguna(token)
      .then((r) => setDaftar(r.data || []))
      .catch((e) => setPesan({ tipe: 'danger', teks: e.message }))
      .finally(() => setMemuat(false));
  }, [token]);

  useEffect(() => {
    if (adalahAdmin) muat();
  }, [adalahAdmin, muat]);

  if (!adalahAdmin) {
    return <div className="alert alert-warning">Halaman ini khusus admin.</div>;
  }

  function galat(e, awalan) {
    if (e.status === 403) return 'Peran kamu tidak diizinkan melakukan ini.';
    return `${awalan}${e.message}`;
  }

  async function tambah(e) {
    e.preventDefault();
    setPesan(null);
    try {
      await api.tambahPengguna(token, { ...baru, username: baru.username.trim() });
      setPesan({ tipe: 'success', teks: `Akun ${baru.username.trim()} berhasil dibuat.` });
      setBaru({ username: '', password: '', peran: 'operator' });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menambah akun: ') });
    }
  }

  async function simpanUbah(p) {
    setPesan(null);
    if (ubah.password && ubah.password.length < 8) {
      return setPesan({ tipe: 'danger', teks: 'Password baru minimal 8 karakter.' });
    }
    const body = {};
    if (ubah.peran !== p.peran) body.peran = ubah.peran;
    if (ubah.password) body.password = ubah.password;
    if (Object.keys(body).length === 0) {
      setUbahId(null);
      return;
    }
    try {
      await api.ubahPengguna(token, p.id_pengguna, body);
      setPesan({ tipe: 'success', teks: `Akun ${p.username} diperbarui.` });
      setUbahId(null);
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal mengubah akun: ') });
    }
  }

  async function hapus(p) {
    if (!window.confirm(`Hapus akun "${p.username}"?\n\nTindakan ini tidak bisa dibatalkan.`)) return;
    setPesan(null);
    try {
      await api.hapusPengguna(token, p.id_pengguna);
      setPesan({ tipe: 'success', teks: `Akun ${p.username} dihapus.` });
      muat();
    } catch (err) {
      setPesan({ tipe: 'danger', teks: galat(err, 'Gagal menghapus akun: ') });
    }
  }

  return (
    <>
      <h1 className="h3 mb-3">Kelola Admin</h1>

      {pesan && (
        <div className={`alert alert-${pesan.tipe} alert-dismissible py-2`} role="alert">
          {pesan.teks}
          <button type="button" className="btn-close" aria-label="Tutup" onClick={() => setPesan(null)} />
        </div>
      )}

      <div className="row g-3">
        <div className="col-12 col-xl-8">
          <div className="card">
            <div className="card-body">
              <h2 className="h5">Daftar akun</h2>
              <div className="table-responsive">
                <table className="table table-sm table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Peran</th>
                      <th className="text-end">Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {memuat && <tr><td colSpan="3" className="text-center text-secondary py-3">Memuat…</td></tr>}
                    {!memuat && daftar.length === 0 && (
                      <tr><td colSpan="3" className="text-center text-secondary py-3">Belum ada akun.</td></tr>
                    )}
                    {daftar.map((p) => {
                      const saya = p.id_pengguna === sesi.pengguna.id_pengguna;
                      const diUbah = ubahId === p.id_pengguna;
                      return (
                        <tr key={p.id_pengguna}>
                          <td>
                            {p.username}
                            {saya && <span className="badge bg-secondary ms-2">Kamu</span>}
                          </td>
                          <td className="text-capitalize">
                            {diUbah ? (
                              <div className="d-flex flex-column gap-1">
                                <select className="form-select form-select-sm" aria-label="Peran" value={ubah.peran}
                                  onChange={(e) => setUbah({ ...ubah, peran: e.target.value })}>
                                  {PERAN.map((r) => <option key={r} value={r}>{r}</option>)}
                                </select>
                                <input type="password" className="form-control form-control-sm" autoComplete="new-password"
                                  maxLength={72} placeholder="Reset password (kosongkan jika tidak)"
                                  value={ubah.password} onChange={(e) => setUbah({ ...ubah, password: e.target.value })} />
                              </div>
                            ) : (
                              p.peran
                            )}
                          </td>
                          <td className="text-end">
                            <div className="d-flex flex-column flex-sm-row justify-content-end gap-1">
                              {diUbah ? (
                                <>
                                  <button type="button" className="btn btn-primary btn-sm" onClick={() => simpanUbah(p)}>Simpan</button>
                                  <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setUbahId(null)}>Batal</button>
                                </>
                              ) : (
                                <>
                                  <button type="button" className="btn btn-outline-primary btn-sm"
                                    onClick={() => { setUbahId(p.id_pengguna); setUbah({ peran: p.peran, password: '' }); }}>
                                    Ubah
                                  </button>
                                  <button type="button" className="btn btn-outline-danger btn-sm" disabled={saya}
                                    title={saya ? 'Tidak bisa menghapus akun sendiri' : ''} onClick={() => hapus(p)}>
                                    Hapus
                                  </button>
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
            <h2 className="h5">Tambah akun</h2>
            <div className="mb-2">
              <label className="form-label small fw-semibold" htmlFor="u-user">Username</label>
              <input id="u-user" className="form-control form-control-sm" required autoComplete="off"
                pattern="[A-Za-z0-9_.\-]{3,50}" title="3-50 karakter: huruf, angka, titik, _ atau -"
                value={baru.username} onChange={(e) => setBaru({ ...baru, username: e.target.value })} />
            </div>
            <div className="mb-2">
              <label className="form-label small fw-semibold" htmlFor="u-pass">Password (min. 8 karakter)</label>
              <input id="u-pass" type="password" className="form-control form-control-sm" required minLength={8} maxLength={72}
                autoComplete="new-password"
                value={baru.password} onChange={(e) => setBaru({ ...baru, password: e.target.value })} />
            </div>
            <div className="mb-3">
              <label className="form-label small fw-semibold" htmlFor="u-peran">Peran</label>
              <select id="u-peran" className="form-select form-select-sm" value={baru.peran}
                onChange={(e) => setBaru({ ...baru, peran: e.target.value })}>
                {PERAN.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <button className="btn btn-primary btn-sm" type="submit">Tambah akun</button>
          </form>
        </div>
      </div>
    </>
  );
}
