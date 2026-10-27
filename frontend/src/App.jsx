import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import PetaPage from './pages/PetaPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import DetailKasusPage from './pages/DetailKasusPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import TambahKasusPage from './pages/TambahKasusPage.jsx';
import EditKasusPage from './pages/EditKasusPage.jsx';
import ProfilPage from './pages/ProfilPage.jsx';
import PenggunaPage from './pages/PenggunaPage.jsx';
import { useAuth } from './auth.jsx';

// Halaman yang hanya boleh dibuka setelah login.
function WajibLogin({ children }) {
  const { sesi } = useAuth();
  const lokasi = useLocation();
  if (!sesi) return <Navigate to="/login" replace state={{ dari: lokasi.pathname }} />;
  return children;
}

// Rute publik: Dashboard, Peta, Statistik, Login.
// Rute admin: Kelola Data, Tambah, Ubah, Profil, Kelola Admin.
// Pendaftaran umum ditutup: akun hanya dibuat admin lewat /admin/pengguna.
export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/peta" element={<PetaPage />} />
        <Route path="/detail-kasus" element={<DetailKasusPage />} />
        <Route path="/detail-kasus-grafik" element={<DetailKasusPage />} />
        <Route path="/detail-kasus-tabel" element={<DetailKasusPage />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/daftar" element={<Navigate to="/login" replace />} />
        <Route path="/admin" element={<WajibLogin><AdminPage /></WajibLogin>} />
        <Route path="/admin/tambah-data" element={<WajibLogin><TambahKasusPage /></WajibLogin>} />
        <Route path="/admin/ubah-data" element={<WajibLogin><EditKasusPage /></WajibLogin>} />
        <Route path="/admin/profil" element={<WajibLogin><ProfilPage /></WajibLogin>} />
        <Route path="/admin/pengguna" element={<WajibLogin><PenggunaPage /></WajibLogin>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
