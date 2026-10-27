import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { api } from '../api.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

// Halaman Statistik Kriminalitas (satu halaman): grafik batang mendatar, lalu tabel + pencarian.
// Alamat: /detail-kasus, /detail-kasus-grafik, /detail-kasus-tabel (halaman sama, hanya posisi gulir yang berbeda).
// Data: GET /api/statistik, GET /api/kasus (berhalaman, limit maks. 100).
const WARNA = { tinggi: '#FF3131', sedang: '#FFC800', rendah: '#20A99B' };
const TINGKAT = {
  tinggi: { teks: 'Sangat Rawan', fg: '#fff' },
  sedang: { teks: 'Cukup Rawan', fg: '#3b2f00' },
  rendah: { teks: 'Tidak Rawan', fg: '#fff' },
};
const angka = (n) => Number(n).toLocaleString('id-ID');
const PER_HALAMAN = 15;

function ambilBaris(r) {
  if (Array.isArray(r)) return r;
  return r?.data || r?.items || r?.kasus || [];
}

// Ambil semua halaman /api/kasus (API membatasi jumlah baris per halaman).
async function ambilSemuaKasus() {
  const LIMIT = 100; // batas maksimal API
  const pertama = await api.kasus({ page: 1, limit: LIMIT });
  const semua = [...ambilBaris(pertama)];
  const total = pertama?.total_data ?? semua.length;
  const jumlahHalaman = Math.ceil(total / LIMIT);

  const sisa = await Promise.all(
    Array.from({ length: Math.max(0, jumlahHalaman - 1) }, (_, i) =>
      api.kasus({ page: i + 2, limit: LIMIT }).then(ambilBaris)
    )
  );
  sisa.forEach((b) => semua.push(...b));
  return semua;
}

function Lencana({ zona }) {
  const t = TINGKAT[zona];
  if (!t) return <span className="text-secondary">-</span>;
  return (
    <span className="badge" style={{ background: WARNA[zona], color: t.fg }}>
      {t.teks}
    </span>
  );
}

function BatangMendatar({ label, nilai, warna }) {
  const data = { labels: label, datasets: [{ data: nilai, backgroundColor: warna, borderRadius: 3 }] };
  const opsi = {
    indexAxis: 'y',
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.parsed.x} kasus` } } },
    scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { ticks: { autoSkip: false } } },
  };
  return <Bar data={data} options={opsi} />;
}

export default function DetailKasusPage() {
  const { pathname } = useLocation();
  const [stat, setStat] = useState(null);
  const [baris, setBaris] = useState([]);
  const [galat, setGalat] = useState('');
  const [cari, setCari] = useState('');
  const [halaman, setHalaman] = useState(1);

  useEffect(() => {
    Promise.all([api.statistik(), ambilSemuaKasus()])
      .then(([s, k]) => {
        setStat(s);
        setBaris(k);
      })
      .catch((e) => setGalat(e.message));
  }, []);

  // Gulir ke bagian grafik/tabel sesuai alamat (/detail-kasus-grafik atau /detail-kasus-tabel).
  useEffect(() => {
    if (!stat) return;
    const id = pathname.endsWith('-tabel') ? 'tabel' : pathname.endsWith('-grafik') ? 'grafik' : null;
    if (id) document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }, [stat, pathname]);

  // Kasus tertinggi per Polsek (jenis dengan jumlah terbesar) dari data /api/kasus.
  const teratas = useMemo(() => {
    const peta = {};
    baris.forEach((b) => {
      if (stat && b.tahun !== undefined && Number(b.tahun) !== Number(stat.tahun)) return;
      if (!b.nama_polsek) return;
      peta[b.nama_polsek] ??= {};
      peta[b.nama_polsek][b.nama_jenis] = (peta[b.nama_polsek][b.nama_jenis] || 0) + Number(b.jumlah || 0);
    });
    const hasil = {};
    Object.entries(peta).forEach(([p, j]) => {
      const [nama, jml] = Object.entries(j).sort((a, b) => b[1] - a[1])[0];
      hasil[p] = { nama, jml };
    });
    return hasil;
  }, [baris, stat]);

  const polsek = useMemo(
    () => (stat ? [...stat.per_polsek].sort((a, b) => a.nama_polsek.localeCompare(b.nama_polsek, 'id')) : []),
    [stat]
  );

  const tersaring = useMemo(() => {
    const q = cari.trim().toLowerCase();
    if (!q) return polsek;
    return polsek.filter(
      (p) =>
        p.nama_polsek.toLowerCase().includes(q) ||
        String(teratas[p.nama_polsek]?.nama ?? '').toLowerCase().includes(q)
    );
  }, [polsek, teratas, cari]);

  useEffect(() => setHalaman(1), [cari]);

  if (galat) {
    return (
      <div className="alert alert-danger" role="alert">
        Data belum bisa dimuat ({galat}). Pastikan backend sudah jalan di <code>http://localhost:3000</code>.
      </div>
    );
  }
  if (!stat) return <p className="text-secondary">Memuat statistik…</p>;

  const jumlahHalaman = Math.max(1, Math.ceil(tersaring.length / PER_HALAMAN));
  const tampil = tersaring.slice((halaman - 1) * PER_HALAMAN, halaman * PER_HALAMAN);
  const adaCluster = polsek.some((p) => p.cluster !== undefined && p.cluster !== null);

  return (
    <>
      <h1 className="h3 mb-3">Statistik Kriminalitas Bandung</h1>

      {/* 1. Grafik (bar chart mendatar) */}
      <div className="card mb-4" id="grafik">
        <div className="card-body">
          <h2 className="h6">Distribusi Kriminalitas per Wilayah Bandung ({stat.tahun})</h2>
          <div className="d-flex flex-wrap gap-3 mb-3 small">
            {['tinggi', 'sedang', 'rendah'].map((z) => (
              <span key={z}>
                <span className={`dot dot-${z}`} /> Zona {z}: <strong>{stat.distribusi_zona[z]}</strong> wilayah
              </span>
            ))}
          </div>
          <div style={{ height: Math.max(420, polsek.length * 24 + 40) }}>
            <BatangMendatar
              label={polsek.map((p) => p.nama_polsek)}
              nilai={polsek.map((p) => p.total_kasus)}
              warna={polsek.map((p) => WARNA[p.kategori_zona])}
            />
          </div>
        </div>
      </div>

      {/* 2. Tabel + pencarian */}
      <div className="card" id="tabel">
        <div className="card-body">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <h2 className="h6 mb-0">Tabel Statistik Kriminalitas Kabupaten Bandung</h2>
            <input
              type="search"
              className="form-control"
              style={{ maxWidth: 320 }}
              placeholder="Cari Polsek atau jenis kasus…"
              value={cari}
              onChange={(e) => setCari(e.target.value)}
              aria-label="Cari kasus"
            />
          </div>

          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Kepolisian Sektor</th>
                  <th>Kasus Tertinggi</th>
                  <th>Jumlah Kasus</th>
                  {adaCluster && <th>Cluster</th>}
                  <th>Tingkat Bahaya</th>
                </tr>
              </thead>
              <tbody>
                {tampil.length === 0 ? (
                  <tr>
                    <td colSpan={adaCluster ? 6 : 5} className="text-center text-secondary py-4">
                      {cari ? `Tidak ditemukan data untuk “${cari}”.` : 'Belum ada data kasus.'}
                    </td>
                  </tr>
                ) : (
                  tampil.map((p, i) => {
                    const t = teratas[p.nama_polsek];
                    return (
                      <tr key={p.nama_polsek}>
                        <td>{(halaman - 1) * PER_HALAMAN + i + 1}</td>
                        <td>{p.nama_polsek}</td>
                        <td>{t ? t.nama : '-'}</td>
                        <td>{t ? angka(t.jml) : angka(p.total_kasus)}</td>
                        {adaCluster && <td>{p.cluster ?? '-'}</td>}
                        <td><Lencana zona={p.kategori_zona} /></td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
            <span className="small text-secondary">{angka(tersaring.length)} wilayah</span>
            <div className="d-flex align-items-center gap-2">
              <button className="btn btn-sm btn-outline-secondary" disabled={halaman <= 1} onClick={() => setHalaman(halaman - 1)}>
                Sebelumnya
              </button>
              <span className="small">Halaman {halaman} / {jumlahHalaman}</span>
              <button className="btn btn-sm btn-outline-secondary" disabled={halaman >= jumlahHalaman} onClick={() => setHalaman(halaman + 1)}>
                Berikutnya
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
