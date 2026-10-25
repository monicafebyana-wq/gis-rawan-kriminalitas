import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

export default function Navbar() {
  const { sesi, logout } = useAuth();
  const navigate = useNavigate();
  const keluar = () => {
    logout();
    navigate('/');
  };
  const linkClass = ({ isActive }) => 'nav-link' + (isActive ? ' active fw-semibold' : '');
  return (
    <nav className="navbar navbar-expand-md navbar-dark navbar-kopi">
      <div className="container-fluid px-3 px-md-4">
        <Link className="navbar-brand" to="/">
          <span className="fw-bold">Peta Rawan Kriminalitas</span>
          <small className="d-block text-secondary" style={{ fontSize: 12 }}>
            Kabupaten Bandung · Data tahun 2024
          </small>
        </Link>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#menuUtama"
          aria-controls="menuUtama"
          aria-expanded="false"
          aria-label="Buka menu"
        >
          <span className="navbar-toggler-icon" />
        </button>
        <div className="collapse navbar-collapse" id="menuUtama">
          <ul className="navbar-nav ms-auto gap-md-1">
            <li className="nav-item">
              <NavLink className={linkClass} to="/" end>Dashboard</NavLink>
            </li>
            <li className="nav-item">
              <NavLink className={linkClass} to="/peta">Peta</NavLink>
            </li>
            {sesi ? (
              <>
                <li className="nav-item">
                  <NavLink className={linkClass} to="/admin">Kelola Data</NavLink>
                </li>
                <li className="nav-item">
                  <button
                    type="button"
                    className="btn btn-outline-light btn-sm ms-md-2 mt-2 mt-md-0"
                    onClick={keluar}
                  >
                    Keluar ({sesi.pengguna.username})
                  </button>
                </li>
              </>
            ) : (
              <li className="nav-item">
                <NavLink className="btn btn-outline-light btn-sm ms-md-2 mt-2 mt-md-0" to="/login">
                  Masuk (Admin)
                </NavLink>
              </li>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
}
