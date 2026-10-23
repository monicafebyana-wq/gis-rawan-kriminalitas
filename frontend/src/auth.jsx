import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from './api.js';

// Sesi login disimpan di sessionStorage: hilang saat tab ditutup, tetap ada saat halaman dimuat ulang.
const KUNCI = 'gis_sesi';
const AuthContext = createContext(null);

function bacaSesi() {
  try {
    const s = JSON.parse(sessionStorage.getItem(KUNCI));
    if (s && s.token && s.kedaluwarsa > Date.now()) return s;
  } catch {
    /* penyimpanan tidak tersedia: anggap belum login */
  }
  return null;
}

function simpanSesi(s) {
  try {
    if (s) sessionStorage.setItem(KUNCI, JSON.stringify(s));
    else sessionStorage.removeItem(KUNCI);
  } catch {
    /* abaikan */
  }
}

export function AuthProvider({ children }) {
  const [sesi, setSesi] = useState(bacaSesi);

  const login = useCallback(async (username, password) => {
    const r = await api.login(username, password);
    const baru = {
      token: r.token,
      pengguna: r.pengguna, // { id_pengguna, username, peran }
      kedaluwarsa: Date.now() + (r.berlaku_detik || 86400) * 1000,
    };
    simpanSesi(baru);
    setSesi(baru);
  }, []);

  const logout = useCallback(() => {
    simpanSesi(null);
    setSesi(null);
  }, []);

  // api.js memberi sinyal ini kalau server menolak token (kedaluwarsa).
  useEffect(() => {
    window.addEventListener('sesi-habis', logout);
    return () => window.removeEventListener('sesi-habis', logout);
  }, [logout]);

  const nilai = useMemo(() => ({ sesi, login, logout }), [sesi, login, logout]);
  return <AuthContext.Provider value={nilai}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
