// Klien API tunggal. Semua halaman memanggil API lewat file ini.
// Alamat dasar: mock server ATAU backend asli (sama: http://localhost:3000/api).
// Ganti lewat file .env (VITE_API_URL) kalau perlu.
// Kontrak endpoint: docs/api-contract.md

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:3000/api';

async function request(path, { params, method = 'GET', body, token } = {}) {
  const url = new URL(BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
  }
  const res = await fetch(url, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    // Format error API: { error: { kode, pesan, detail } }
    throw new Error(data?.error?.pesan || `Permintaan gagal (${res.status})`);
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
  // Admin (butuh token)
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: { username, password } }),
  me: (token) => request('/auth/me', { token }),
};
