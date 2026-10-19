import { NavLink, Link } from 'react-router-dom';

export default function Navbar() {
  const linkClass = ({ isActive }) => 'nav-link' + (isActive ? ' active fw-semibold' : '');
  return (
    <nav className="navbar navbar-expand-md bg-white border-bottom">
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
              <NavLink className={linkClass} to="/" end>Peta</NavLink>
            </li>
            <li className="nav-item">
              <NavLink className={linkClass} to="/dashboard">Ringkasan Data</NavLink>
            </li>
            <li className="nav-item">
              <NavLink className="btn btn-outline-secondary btn-sm ms-md-2 mt-2 mt-md-0" to="/login">
                Masuk (Admin)
              </NavLink>
            </li>
          </ul>
        </div>
      </div>
    </nav>
  );
}
