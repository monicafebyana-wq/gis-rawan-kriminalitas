import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import PetaPage from './pages/PetaPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import AdminPage from './pages/AdminPage.jsx';
import { useAuth } from './auth.jsx';

// Halaman yang hanya boleh dibuka setelah login.
function WajibLogin({ children }) {
  const { sesi } = useAuth();
  const lokasi = useLocation();
  if (!sesi) return <Navigate to="/login" replace state={{ dari: lokasi.pathname }} />;
  return children;
}

// Rute sesuai wireframe: Peta (beranda), Ringkasan Data, Daftar, Login, Admin.
export default function App() {
  return (
    <>
      <Navbar />
      <main className="container-fluid px-3 px-md-4 py-3">
        <Routes>
          <Route path="/" element={<PetaPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
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
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}