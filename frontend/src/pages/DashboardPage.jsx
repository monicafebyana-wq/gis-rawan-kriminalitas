import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip } from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import { api } from '../api.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip);

// Halaman Dashboard (beranda): kartu ringkasan + grafik TOP 5 + tren.
// Data dari GET /api/statistik dan GET /api/statistik/tren.
const WARNA = { tinggi: '#FF3131', sedang: '#FFC800', rendah: '#20A99B' };
const angka = (n) => Number(n).toLocaleString('id-ID');
const TOP = 5;

function Kartu({ judul, nilai, catatan }) {
  return (
    <div className="col-6 col-lg-3">
      <div className="card h-100">
        <div className="card-body">
          <div className="text-secondary">{judul}</div>
          <div className="fs-3 fw-bold">{nilai}</div>
          {catatan && <div className="small text-secondary">{catatan}</div>}
        </div>
      </div>
    </div>
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
  return (
    <div style={{ height: Math.max(220, label.length * 24 + 40) }}>
      <Bar data={data} options={opsi} />
    </div>
  );
}

export default function DashboardPage() {
  const [stat, setStat] = useState(null);
  const [tren, setTren] = useState([]);
  const [galat, setGalat] = useState('');

  useEffect(() => {
    Promise.all([api.statistik(), api.tren()])
      .then(([s, t]) => {
        setStat(s);
        setTren(t.data);
      })
      .catch((e) => setGalat(e.message));
  }, []);

  if (galat) {
    return (
      <div className="alert alert-danger" role="alert">
        Data belum bisa dimuat ({galat}). Pastikan backend sudah jalan di <code>http://localhost:3000</code>.
      </div>
    );
  }
  if (!stat) return <p className="text-secondary">Memuat dashboard…</p>;

  const namaJenisTop = stat.top_jenis.map((j) => j.nama_jenis).join(', ');

  // Top 5: urut dari terbanyak, ambil 5 teratas.
  const topPolsek = [...stat.per_polsek].sort((a, b) => b.total_kasus - a.total_kasus).slice(0, TOP);
  const topJenis = [...stat.per_jenis].sort((a, b) => b.jumlah - a.jumlah).slice(0, TOP);

  return (
    <>
      <section className="hero-kopi mb-4">
        <div className="hero-kicker">Kabupaten Bandung · Data tahun {stat.tahun}</div>
        <h1 className="h2">Dashboard kasus kejahatan {stat.tahun}</h1>
        <p className="mb-3">Di mana kasus paling banyak, dan jenis apa yang paling sering terjadi.</p>
        <div className="d-flex flex-wrap gap-2">
          <Link className="btn btn-primary" to="/peta">Lihat peta kerawanan</Link>
          <Link className="btn btn-outline-secondary" to="/detail-kasus-grafik">Lihat detail kasus</Link>
        </div>
      </section>

      <div className="row g-3 mb-3">
        <Kartu judul="Total kasus" nilai={angka(stat.total_kasus)} catatan={`di ${stat.jumlah_polsek} wilayah Polsek`} />
        <Kartu
          judul="Paling banyak kasus"
          nilai={stat.polsek_tertinggi.nama_polsek}
          catatan={`${angka(stat.polsek_tertinggi.total_kasus)} kasus`}
        />
        <Kartu
          judul="Paling sedikit kasus"
          nilai={stat.polsek_terendah.nama_polsek}
          catatan={`${angka(stat.polsek_terendah.total_kasus)} kasus`}
        />
        <Kartu
          judul="4 jenis terbanyak"
          nilai={`${String(stat.persen_top_jenis).replace('.', ',')}%`}
          catatan={`dari seluruh kasus: ${namaJenisTop}`}
        />
      </div>

      <div className="d-flex flex-wrap gap-3 mb-3 small">
        {['tinggi', 'sedang', 'rendah'].map((z) => (
          <span key={z}>
            <span className={`dot dot-${z}`} /> Zona {z}: <strong>{stat.distribusi_zona[z]}</strong> wilayah
          </span>
        ))}
      </div>

      <div className="row g-3">
        <div className="col-12 col-lg-6">
          <div className="card h-100">
            <div className="card-body">
              <h2 className="h6">Top {TOP} Polsek dengan kasus terbanyak</h2>
              <BatangMendatar
                label={topPolsek.map((p) => p.nama_polsek)}
                nilai={topPolsek.map((p) => p.total_kasus)}
                warna={topPolsek.map((p) => WARNA[p.kategori_zona])}
              />
            </div>
          </div>
        </div>
        <div className="col-12 col-lg-6">
          <div className="card h-100">
            <div className="card-body">
              <h2 className="h6">Top {TOP} jenis kejahatan</h2>
              <BatangMendatar
                label={topJenis.map((j) => j.nama_jenis)}
                nilai={topJenis.map((j) => j.jumlah)}
                warna="#C4601A"
              />
            </div>
          </div>
        </div>
        <div className="col-12">
          <div className="card">
            <div className="card-body">
              <h2 className="h6">Tren kasus dari tahun ke tahun</h2>
              <div style={{ height: 240 }}>
                <Line
                  data={{
                    labels: tren.map((t) => String(t.tahun)),
                    datasets: [{ data: tren.map((t) => t.total_kasus), borderColor: '#4B5C3C', backgroundColor: '#4B5C3C', pointRadius: 5, tension: 0.2 }],
                  }}
                  options={{
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => ` ${c.parsed.y} kasus` } } },
                    scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
                  }}
                />
              </div>
              {tren.length < 2 && (
                <p className="small text-secondary mb-0">
                  Saat ini baru ada data tahun {tren[0]?.tahun}. Garis akan terbentuk setelah data tahun lain ditambahkan.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
