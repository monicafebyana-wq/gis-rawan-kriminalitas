import { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useAuth } from '../auth.jsx';

// Riwayat Perubahan (khusus admin): siapa mengubah apa dan kapan. Endpoint: GET /api/audit.
// Password tidak pernah dicatat. Perubahan yang gagal/dibatalkan tidak muncul di sini.
const BATAS = 20;
const ENTITAS = ['kasus', 'titik', 'pengguna', 'polsek', 'jenis', 'poligon'];
const AKSI = ['tambah', 'ubah', 'hapus', 'impor', 'ubah_password'];
const WARNA_AKSI = { tambah: 'success', ubah: 'primary', hapus: 'danger', impor: 'info', ubah_password: 'secondary' };
const KOSONG = { entitas: '', aksi: '', username: '', dari: '', sampai: '' };

function waktuLokal(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('id-ID', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function AuditPage() {
  const { sesi } = useAuth();
  const adalahAdmin = sesi.pengguna.peran === 'admin';
  const [form, setForm] = useState(KOSONG);
  const [terapkan, setTerapkan] = useState(KOSONG);
  const [halaman, setHalaman] = useState(1);
  const [hasil, setHasil] = useState(null);
  const [memuat, setMemuat] = useState(false);
  const [galat, setGalat] = useState('');

  useEffect(() => {
    if (!adalahAdmin) return;
    setMemuat(true);
    setGalat('');
    api
      .audit(sesi.token, { ...terapkan, page: halaman, limit: BATAS })
      .then(setHasil)
      .catch((e) => setGalat(e.status === 403 ? 'Peran kamu tidak diizinkan melihat riwayat.' : e.message))
      .finally(() => setMemuat(false));
  }, [adalahAdmin, sesi.token, terapkan, halaman]);

  if (!adalahAdmin) return <div className="alert alert-warning">Halaman ini khusus admin.</div>;

  function cari(e) {
    e.preventDefault();
    setTerapkan({ ...form, username: form.username.trim() });
    setHalaman(1);
  }

  function atur() {
    setForm(KOSONG);
    setTerapkan(KOSONG);
    setHalaman(1);
  }

  const total = hasil ? hasil.total_data : 0;
  const jumlahHalaman = Math.max(1, Math.ceil(total / BATAS));

  return (
    <>
      <h1 className="h3 mb-1">Riwayat Perubahan</h1>
      <p className="small text-secondary">Catatan perubahan data dan akun, terbaru di atas.</p>

      <form className="card card-body mb-3" onSubmit={cari}>
        <div className="row g-2 align-items-end">
          <div className="col-6 col-md-2">
            <label className="form-label small fw-semibold" htmlFor="a-ent">Data</label>
            <select id="a-ent" className="form-select form-select-sm" value={form.entitas} onChange={(e) => setForm({ ...form, entitas: e.target.value })}>
              <option value="">Semua</option>
              {ENTITAS.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label small fw-semibold" htmlFor="a-aksi">Aksi</label>
            <select id="a-aksi" className="form-select form-select-sm" value={form.aksi} onChange={(e) => setForm({ ...form, aksi: e.target.value })}>
              <option value="">Semua</option>
              {AKSI.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </div>
          <div className="col-12 col-md-2">
            <label className="form-label small fw-semibold" htmlFor="a-user">Username</label>
            <input id="a-user" className="form-control form-control-sm" maxLength={50} value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })} />
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label small fw-semibold" htmlFor="a-dari">Dari tanggal</label>
            <input id="a-dari" type="date" className="form-control form-control-sm" value={form.dari}
              onChange={(e) => setForm({ ...form, dari: e.target.value })} />
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label small fw-semibold" htmlFor="a-sampai">Sampai tanggal</label>
            <input id="a-sampai" type="date" className="form-control form-control-sm" value={form.sampai}
              onChange={(e) => setForm({ ...form, sampai: e.target.value })} />
          </div>
          <div className="col-12 col-md-2 d-flex gap-2">
            <button className="btn btn-primary btn-sm flex-fill" type="submit">Cari</button>
            <button className="btn btn-outline-secondary btn-sm" type="button" onClick={atur}>Atur ulang</button>
          </div>
        </div>
      </form>

      {galat && <div className="alert alert-danger py-2" role="alert">{galat}</div>}

      <div className="card">
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-sm table-hover align-top mb-2 tabel-admin">
              <thead>
                <tr>
                  <th>Waktu</th>
                  <th>Oleh</th>
                  <th>Aksi</th>
                  <th>Data</th>
                  <th>Rincian</th>
                </tr>
              </thead>
              <tbody>
                {hasil && hasil.data.length === 0 && (
                  <tr><td colSpan="5" className="text-center text-secondary py-3">Belum ada catatan yang cocok.</td></tr>
                )}
                {hasil && hasil.data.map((r) => (
                  <tr key={r.id_log}>
                    <td className="text-nowrap">{waktuLokal(r.waktu)}</td>
                    <td>{r.username}</td>
                    <td><span className={`badge bg-${WARNA_AKSI[r.aksi] || 'secondary'}`}>{r.aksi}</span></td>
                    <td>{r.entitas}{r.id_entitas ? ` #${r.id_entitas}` : ''}</td>
                    <td className="detail-audit">
                      {r.detail ? (
                        <details>
                          <summary className="small">Lihat</summary>
                          <pre>{JSON.stringify(r.detail, null, 2)}</pre>
                        </details>
                      ) : <span className="text-secondary">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
            <div className="small text-secondary">{memuat ? 'Memuat…' : `${total} catatan · halaman ${halaman} dari ${jumlahHalaman}`}</div>
            <div className="btn-group btn-group-sm">
              <button type="button" className="btn btn-outline-secondary" disabled={halaman <= 1} onClick={() => setHalaman(halaman - 1)}>‹ Sebelumnya</button>
              <button type="button" className="btn btn-outline-secondary" disabled={halaman >= jumlahHalaman} onClick={() => setHalaman(halaman + 1)}>Berikutnya ›</button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
