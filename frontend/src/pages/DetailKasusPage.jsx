import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { api } from '../api.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

// Halaman Statistik Kriminalitas (satu halaman): #grafik (bar chart mendatar + ringkasan), lalu #tabel + pencarian.
// Data: GET /api/statistik, GET /api/statistik/tren, GET /api/kasus (berhalaman).
const WARNA = { tinggi: '#D96C7B', sedang: '#F5B58A', rendah: '#9ACDB8' };
const TINGKAT = {
  tinggi: { teks: 'Sangat Rawan', fg: '#4A1B22' },
  sedang: { teks: 'Cukup Rawan', fg: '#5A3414' },
  rendah: { teks: 'Tidak Rawan', fg: '#16463A' },
};
const angka = (n) => Number(n).toLocaleString('id-ID');
const PER_HALAMAN = 15;

function ambilBaris(r) {
  if (Array.isArray(r)) return r;
  return r?.data || r?.items || r?.kasus || [];
}

// Ambil semua halaman /api/kasus. Limit 20 (default API) supaya tidak ditolak validasi.
async function ambilSemuaKasus() {
  const LIMIT = 20;
  const pertama = await api.kasus({ page: 1, limit: LIMIT });
  const semua = [...ambilBaris(pertama)];
  const total = pertama?.total_data ?? semua.length;
  const jumlahHalaman = Math.ceil(total / LIMIT);

  const sisa = await Promise.all(
    Array.from({ length: Math.max(0, jumlahHalaman - 1) }, (_, i) =>
      api.kasus({ page: i + 2, limit: LIMIT }).then(ambilBaris)
    )
  );
  sisa.forEach((baris) => semua.push(...baris));
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
  const { hash, pathname } = useLocation();
  const [stat, setStat] = useState(null);
  const [tren, setTren] = useState([]);
  const [baris, setBaris] = useState([]);
  const [galat, setGalat] = useState('');
  const [cari, setCari] = useState('');
  const [halaman, setHalaman] = useState(1);

  useEffect(() => {
    Promise.all([api.statistik(), api.tren(), ambilSemuaKasus()])
      .then(([s, t, k]) => {
        setStat(s);
        setTren(t?.data || []);
        setBaris(k);
      })
      .catch((e) => setGalat(e.message));
  }, []);

  // Scroll ke #grafik / #tabel setelah data tampil (dari klik submenu sidebar).
useEffect(() => {
  if (!stat) return;
  let id = hash ? hash.slice(1) : '';
  if (!id) id = pathname.endsWith('-tabel') ? 'tabel' : 'grafik';
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}, [stat, hash, pathname]);

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

  // Ringkasan statistik
  const urut = [...tren].sort((a, b) => a.tahun - b.tahun);
  let trend = 'Belum ada pembanding';
  let warnaTrend = 'text-secondary';
  if (urut.length >= 2) {
    const a = urut[urut.length - 2].total_kasus;
    const b = urut[urut.length - 1].total_kasus;
    trend = b > a ? 'Meningkat' : b < a ? 'Menurun' : 'Stabil';
    warnaTrend = b > a ? 'text-danger' : b < a ? 'text-success' : 'text-secondary';
  }

  const jumlahHalaman = Math.max(1, Math.ceil(tersaring.length / PER_HALAMAN));
  const tampil = tersaring.slice((halaman - 1) * PER_HALAMAN, halaman * PER_HALAMAN);
  const adaCluster = polsek.some((p) => p.cluster !== undefined && p.cluster !== null);

  return (
    <>
      <h1 className="h3 mb-3">Statistik Kriminalitas Bandung</h1>

      {/* 1. Grafik (bar chart mendatar) + ringkasan */}
      <div className="row g-3 mb-4" id="grafik">
        <div className="col-12 col-lg-8">
          <div className="card h-100">
            <div className="card-body">
              <h2 className="h6">Distribusi Kriminalitas per Wilayah Bandung ({stat.tahun})</h2>
              <div style={{ height: Math.max(420, polsek.length * 24 + 40) }}>
                <BatangMendatar
                  label={polsek.map((p) => p.nama_polsek)}
                  nilai={polsek.map((p) => p.total_kasus)}
                  warna={polsek.map((p) => WARNA[p.kategori_zona])}
                />
              </div>
            </div>
          </div>
        </div>
        <div className="col-12 col-lg-4">
          <div className="card h-100">
            <div className="card-body">
              <h2 className="h6">Ringkasan Statistik</h2>
              <div className="text-secondary mt-3">Total Kasus</div>
              <div className="fs-3 fw-bold">{angka(stat.total_kasus)}</div>
              <div className="text-secondary mt-3">Tertinggi</div>
              <div className="fs-5 fw-bold">
                {stat.polsek_tertinggi.nama_polsek} ({angka(stat.polsek_tertinggi.total_kasus)})
              </div>
              <div className="text-secondary mt-3">Terendah</div>
              <div className="fs-5 fw-bold">
                {stat.polsek_terendah.nama_polsek} ({angka(stat.polsek_terendah.total_kasus)})
              </div>
              <div className="text-secondary mt-3">Trend</div>
              <div className={`fs-5 fw-bold ${warnaTrend}`}>{trend}</div>
            </div>
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