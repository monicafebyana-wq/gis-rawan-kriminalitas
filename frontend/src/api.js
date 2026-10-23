// Klien API tunggal. Semua halaman memanggil API lewat file ini.
// Alamat dasar: mock server ATAU backend asli (sama: http://localhost:3000/api).
// Ganti lewat file .env (VITE_API_URL) kalau perlu.
// Kontrak endpoint: docs/api-contract.md

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

async function request(path, { params, method = 'GET', body, form, token } = {}) {
  const url = new URL(BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }

  let res;
  try {
    res = await fetch(url, {
      method,
      headers: {
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      // form = FormData (unggah berkas); browser mengatur Content-Type sendiri
      body: form ? form : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error('Tidak bisa terhubung ke server. Pastikan backend (atau mock server) sudah jalan.');
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    // Token kedaluwarsa/ditolak: beri tahu aplikasi supaya otomatis keluar.
    if (res.status === 401 && token) window.dispatchEvent(new Event('sesi-habis'));
    // Format error API: { error: { kode, pesan, detail } }
    const err = new Error(data?.error?.pesan || `Permintaan gagal (${res.status})`);
    err.status = res.status;
    err.kode = data?.error?.kode;
    err.detail = data?.error?.detail || [];
    throw err;
  }
  return data;
}

export const api = {
  // Publik
  polsek: (params) => request('/polsek', { params }), // GeoJSON peta utama
  polsekDetail: (id, params) => request(`/polsek/${id}`, { params }),
  jenis: () => request('/jenis'),
  tahun: () => request('/tahun'),
  kasus: (params) => request('/kasus', { params }),
  statistik: (params) => request('/statistik', { params }),
  tren: (params) => request('/statistik/tren', { params }),
  // Login & pendaftaran
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: { username, password } }),
  register: (username, password) =>
    request('/auth/register', { method: 'POST', body: { username, password } }),
  me: (token) => request('/auth/me', { token }),
  // Admin / operator (butuh token)
  tambahKasus: (token, body) => request('/kasus', { method: 'POST', body, token }),
  ubahKasus: (token, id, jumlah) => request(`/kasus/${id}`, { method: 'PUT', body: { jumlah }, token }),
  hapusKasus: (token, id) => request(`/kasus/${id}`, { method: 'DELETE', token }), // khusus admin
  imporCsv: (token, form) => request('/import/csv', { method: 'POST', form, token }),
};