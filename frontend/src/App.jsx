import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Layout from './components/Layout.jsx';
import PetaPage from './pages/PetaPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import TambahKasusPage from './pages/TambahKasusPage.jsx';
import { useAuth } from './auth.jsx';

// Halaman yang hanya boleh dibuka setelah login.
function WajibLogin({ children }) {
  const { sesi } = useAuth();
  const lokasi = useLocation();
  if (!sesi) return <Navigate to="/login" replace state={{ dari: lokasi.pathname }} />;
  return children;
}

// Rute: Dashboard (beranda), Peta, Login, Daftar, Kelola Data, Tambah Data.
export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/peta" element={<PetaPage />} />
        <Route path="/dashboard" element={<Navigate to="/" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/daftar" element={<RegisterPage />} />
        <Route
          path="/admin"
          element={
            <WajibLogin>
              <AdminPage />
            </WajibLogin>
          }
        />
        <Route
          path="/admin/tambah-data"
          element={
            <WajibLogin>
              <TambahKasusPage />
            </WajibLogin>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
