import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import PetaPage from './pages/PetaPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import AdminPage from './pages/AdminPage.jsx';

// Rute sesuai wireframe: Peta (beranda), Ringkasan Data, Login, Admin.
export default function App() {
  return (
    <>
      <Navbar />
      <main className="container-fluid px-3 px-md-4 py-3">
        <Routes>
          <Route path="/" element={<PetaPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
