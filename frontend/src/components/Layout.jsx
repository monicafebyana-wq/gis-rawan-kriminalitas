import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import { Ikon } from './Ikon.jsx';

// Kerangka halaman: sidebar di kiri (menu + ikon), bilah atas, lalu isi halaman.
// Desktop: sidebar bisa diciutkan jadi ikon saja. HP: sidebar muncul dari kiri lewat tombol menu.

const JUDUL = {
  '/': 'Dashboard',
  '/peta': 'Peta Rawan Kriminalitas',
  '/detail-kasus': 'Statistik Kriminalitas',
  '/detail-kasus-grafik': 'Statistik Kriminalitas',
  '/detail-kasus-tabel': 'Statistik Kriminalitas',
  '/admin': 'Kelola Data',
  '/admin/tambah-data': 'Tambah Data',
  '/admin/ubah-data': 'Ubah Data',
  '/admin/profil': 'Profil',
  '/admin/pengguna': 'Kelola Admin',
  '/login': 'Masuk Admin',
};

function bacaRingkas() {
  try {
    return localStorage.getItem('gis_ringkas') === '1';
  } catch {
    return false;
  }
}

export default function Layout({ children }) {
  const { sesi, logout } = useAuth();
  const navigate = useNavigate();
  const lokasi = useLocation();
  const [ringkas, setRingkas] = useState(bacaRingkas); // sidebar hanya ikon (desktop)
  const [terbuka, setTerbuka] = useState(false); // sidebar terbuka (HP)
  const [statBuka, setStatBuka] = useState(lokasi.pathname.startsWith('/detail-kasus')); // submenu Statistik

  // Pindah halaman: tutup sidebar di HP.
  useEffect(() => {
    setTerbuka(false);
  }, [lokasi.pathname]);

  function ubahRingkas() {
    const nilai = !ringkas;
    setRingkas(nilai);
    try {
      localStorage.setItem('gis_ringkas', nilai ? '1' : '0');
    } catch {
      /* tidak apa-apa kalau penyimpanan browser tidak tersedia */
    }
  }

  function keluar() {
    logout();
    navigate('/');
  }

  const kelas = ({ isActive }) => 'menu-item' + (isActive ? ' aktif' : '');
  const judul = JUDUL[lokasi.pathname] || 'Peta Rawan Kriminalitas';
  const diStatistik = lokasi.pathname.startsWith('/detail-kasus');
  const adalahAdmin = sesi?.pengguna.peran === 'admin';

  return (
    <div className={`app-shell${ringkas ? ' ringkas' : ''}${terbuka ? ' terbuka' : ''}`}>
      <aside className="sidebar" aria-label="Menu utama">
        <div className="sidebar-atas">
          <Link to="/" className="sidebar-brand" title="Peta Rawan Kriminalitas">
            <span className="logo-kotak">
              <Ikon nama="pin" ukuran={22} />
            </span>
            <span className="teks">
              <strong>PETA RAWAN</strong>
              <small>KRIMINALITAS · KAB. BANDUNG</small>
            </span>
          </Link>
          <button
            type="button"
            className="tombol-tutup-hp"
            aria-label="Tutup menu"
            onClick={() => setTerbuka(false)}
          >
            <Ikon nama="tutup" />
          </button>
        </div>

        <nav className="sidebar-menu">
          <div className="menu-grup teks">Menu</div>
          <NavLink end to="/" className={kelas} title="Dashboard">
            <Ikon nama="dashboard" />
            <span className="teks">Dashboard</span>
          </NavLink>
          <NavLink to="/peta" className={kelas} title="Peta Rawan Kriminalitas">
            <Ikon nama="peta" />
            <span className="teks">Peta Rawan Kriminalitas</span>
          </NavLink>

          {/* Statistik Kriminalitas: tombol yang membuka submenu Grafik & Tabel */}
          <button
            type="button"
            className={'menu-item' + (diStatistik ? ' aktif' : '')}
            onClick={() => setStatBuka(!statBuka)}
            title="Statistik Kriminalitas"
          >
            <Ikon nama="data" />
            <span className="teks">Statistik Kriminalitas</span>
          </button>
          {statBuka && (
            <div className="submenu teks">
              <NavLink to="/detail-kasus-grafik" className={kelas}>Grafik</NavLink>
              <NavLink to="/detail-kasus-tabel" className={kelas}>Tabel</NavLink>
            </div>
          )}

          <div className="menu-grup teks">Pengelola</div>
          {sesi ? (
            <>
              <NavLink to="/admin" end className={kelas} title="Kelola Data">
                <Ikon nama="data" />
                <span className="teks">Kelola Data</span>
              </NavLink>
              {adalahAdmin && (
                <NavLink to="/admin/pengguna" className={kelas} title="Kelola Admin">
                  <Ikon nama="data" />
                  <span className="teks">Kelola Admin</span>
                </NavLink>
              )}
              <NavLink to="/admin/profil" className={kelas} title="Profil">
                <Ikon nama="masuk" />
                <span className="teks">Profil</span>
              </NavLink>
              <button type="button" className="menu-item" onClick={keluar} title="Keluar">
                <Ikon nama="keluar" />
                <span className="teks">Keluar ({sesi.pengguna.username})</span>
              </button>
            </>
          ) : (
            <NavLink to="/login" className={kelas} title="Masuk Admin">
              <Ikon nama="masuk" />
              <span className="teks">Masuk Admin</span>
            </NavLink>
          )}
        </nav>

        <button
          type="button"
          className="tombol-ringkas"
          onClick={ubahRingkas}
          aria-label={ringkas ? 'Lebarkan menu' : 'Ciutkan menu'}
          title={ringkas ? 'Lebarkan menu' : 'Ciutkan menu'}
        >
          <Ikon nama={ringkas ? 'kanan' : 'kiri'} />
        </button>
      </aside>

      {terbuka && <div className="sidebar-latar" onClick={() => setTerbuka(false)} />}

      <div className="app-main">
        <header className="topbar">
          <div className="d-flex align-items-center gap-2">
            <button
              type="button"
              className="tombol-menu-hp"
              aria-label="Buka menu"
              onClick={() => setTerbuka(true)}
            >
              <Ikon nama="menu" />
            </button>
            <span className="judul-topbar">{judul}</span>
          </div>
          {sesi && (
            <span className="chip-pengguna">
              {sesi.pengguna.username} · {sesi.pengguna.peran}
            </span>
          )}
        </header>
        <main className="konten">{children}</main>
      </div>
    </div>
  );
}
