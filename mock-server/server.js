/*
 * Mock server — meniru docs/api-contract.md memakai data asli di data/bersih/*.csv
 * Tanpa dependensi (hanya Node.js >= 16).
 *
 *   cd mock-server && node server.js        (atau: npm start)
 *   PORT=3001 node server.js                (ganti port)
 *
 * Geometri poligon: pakai data/geojson/polsek.geojson atau polsek_poligon.geojson kalau ada (hasil kerja data spasial),
 * kalau tidak ada -> kotak DUMMY dari data/mock/polsek.json.
 * Data kasus disimpan di memori: POST/PUT/DELETE berfungsi, tapi kembali ke awal saat server di-restart.
 * Login: admin / admin123 (peran admin), operator / operator123 (peran operator).
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const PORT = process.env.PORT || 3000;

// ---------- load data ----------
function readCsv(p) {
  const [head, ...rows] = fs.readFileSync(p, 'utf8').trim().split(/\r?\n/);
  const cols = head.split(',');
  return rows.map(r => { const v = r.split(','); const o = {}; cols.forEach((c, i) => (o[c] = v[i])); return o; });
}
const B = f => path.join(ROOT, 'data', 'bersih', f);
const polsek = readCsv(B('polsek.csv')).map(r => ({ id_polsek: +r.id_polsek, nama_polsek: r.nama_polsek }));
const jenis = readCsv(B('jenis_kejahatan.csv')).map(r => ({ id_jenis: +r.id_jenis, kode_jenis: r.kode_jenis, nama_jenis: r.nama_jenis }));
const kasusAwal = readCsv(B('kasus_kejahatan.csv')).map(r => ({ id_kasus: +r.id_kasus, id_polsek: +r.id_polsek, id_jenis: +r.id_jenis, tahun: +r.tahun, jumlah: +r.jumlah }));
let kasus = kasusAwal.map(k => ({ ...k }));
let nextId = Math.max(...kasus.map(k => k.id_kasus)) + 1;

function loadGeometry() {
  const dummy = path.join(ROOT, 'data', 'mock', 'polsek.json');
  const kandidat = ['polsek.geojson', 'polsek_poligon.geojson'].map(n => path.join(ROOT, 'data', 'geojson', n));
  const src = kandidat.find(p => fs.existsSync(p)) || dummy;
  const fc = JSON.parse(fs.readFileSync(src, 'utf8'));
  const map = {};
  fc.features.forEach(f => { map[f.properties.id_polsek] = f.geometry; });
  console.log(`Geometri dari: ${path.relative(ROOT, src)}${src === dummy ? '  (DUMMY - kotak grid)' : ''}`);
  return map;
}
const geom = loadGeometry();

function pusat(g) { // titik tengah bounding box
  const pts = [];
  (function walk(c) { if (typeof c[0] === 'number') pts.push(c); else c.forEach(walk); })(g.coordinates);
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  return { lat: +((Math.min(...ys) + Math.max(...ys)) / 2).toFixed(5), lng: +((Math.min(...xs) + Math.max(...xs)) / 2).toFixed(5) };
}

const USERS = {
  admin: { password: 'admin123', id_pengguna: 1, peran: 'admin' },
  operator: { password: 'operator123', id_pengguna: 2, peran: 'operator' },
};

// ---------- helpers ----------
const zonaOf = n => (n >= 60 ? 'tinggi' : n >= 30 ? 'sedang' : 'rendah');
class ApiError extends Error { constructor(status, kode, pesan, detail = []) { super(pesan); this.status = status; this.kode = kode; this.detail = detail; } }
const bad = (pesan, detail) => new ApiError(400, 'VALIDASI_GAGAL', pesan, detail);

function intList(q, name) {
  if (q.get(name) === null || q.get(name) === '') return null;
  const arr = q.get(name).split(',').map(s => s.trim());
  if (arr.some(s => !/^\d+$/.test(s))) throw bad(`Parameter ${name} harus berupa angka dipisah koma`, [name]);
  return arr.map(Number);
}
function tahunParam(q) {
  const t = q.get('tahun');
  if (t === null || t === '') return Math.max(...kasus.map(k => k.tahun));
  if (!/^\d{4}$/.test(t)) throw bad('Parameter tahun harus berupa angka', ['tahun']);
  return +t;
}
function zonaList(q) {
  const z = q.get('zona'); if (!z) return null;
  const arr = z.split(',').map(s => s.trim());
  if (arr.some(s => !['tinggi', 'sedang', 'rendah'].includes(s))) throw bad('Parameter zona harus tinggi/sedang/rendah', ['zona']);
  return arr;
}
function rekap(tahun, jenisF) { // per polsek
  return polsek.map(p => {
    const rows = kasus.filter(k => k.id_polsek === p.id_polsek && k.tahun === tahun);
    const semua = rows.reduce((a, k) => a + k.jumlah, 0);
    const total = jenisF ? rows.filter(k => jenisF.includes(k.id_jenis)).reduce((a, k) => a + k.jumlah, 0) : semua;
    return { ...p, tahun, total_kasus: total, total_semua_jenis: semua, kategori_zona: zonaOf(semua) };
  });
}
const jenisById = id => jenis.find(j => j.id_jenis === id);
const polsekById = id => polsek.find(p => p.id_polsek === id);

function auth(req, minPeran) {
  const h = req.headers['authorization'] || '';
  const m = h.match(/^Bearer mock-(\w+)$/);
  if (!m || !USERS[m[1]]) throw new ApiError(401, 'TIDAK_TERAUTENTIKASI', 'Token tidak ada atau tidak valid');
  const u = { username: m[1], ...USERS[m[1]] };
  if (minPeran === 'admin' && u.peran !== 'admin') throw new ApiError(403, 'TIDAK_DIIZINKAN', 'Hanya admin yang boleh melakukan aksi ini');
  return u;
}
function readBody(req) {
  return new Promise(res => { const c = []; req.on('data', d => c.push(d)); req.on('end', () => res(Buffer.concat(c).toString('utf8'))); });
}
async function jsonBody(req) {
  const t = await readBody(req);
  try { return t ? JSON.parse(t) : {}; } catch { throw bad('Body harus berupa JSON yang valid'); }
}

// ---------- routes ----------
async function handle(req, res, u) {
  const q = u.searchParams, p = u.pathname.replace(/\/+$/, ''), m = req.method;
  let r;

  if (m === 'GET' && p === '/api/polsek') {
    const tahun = tahunParam(q), jf = intList(q, 'jenis'), pf = intList(q, 'polsek'), zf = zonaList(q);
    const feats = rekap(tahun, jf)
      .filter(x => (!pf || pf.includes(x.id_polsek)) && (!zf || zf.includes(x.kategori_zona)))
      .map(x => ({ type: 'Feature', geometry: geom[x.id_polsek], properties: { ...x, pusat: pusat(geom[x.id_polsek]) } }));
    return send(res, 200, { type: 'FeatureCollection', features: feats });
  }
  if (m === 'GET' && (r = p.match(/^\/api\/polsek\/(\d+)$/))) {
    const id = +r[1], pl = polsekById(id);
    if (!pl) throw new ApiError(404, 'TIDAK_DITEMUKAN', `Polsek dengan id ${id} tidak ditemukan`);
    const tahun = tahunParam(q);
    const rows = kasus.filter(k => k.id_polsek === id && k.tahun === tahun);
    const total = rows.reduce((a, k) => a + k.jumlah, 0);
    const rincian = rows.filter(k => k.jumlah > 0).sort((a, b) => b.jumlah - a.jumlah || a.id_jenis - b.id_jenis)
      .map(k => ({ ...jenisById(k.id_jenis), jumlah: k.jumlah }));
    return send(res, 200, { id_polsek: id, nama_polsek: pl.nama_polsek, tahun, total_kasus: total, kategori_zona: zonaOf(total), rincian_jenis: rincian });
  }
  if (m === 'GET' && p === '/api/jenis') return send(res, 200, { data: jenis });
  if (m === 'GET' && p === '/api/tahun') {
    const t = [...new Set(kasus.map(k => k.tahun))].sort();
    return send(res, 200, { data: t, terbaru: t[t.length - 1] });
  }
  if (m === 'GET' && p === '/api/kasus') {
    const tahun = tahunParam(q), pf = intList(q, 'polsek'), jf = intList(q, 'jenis');
    const page = Math.max(1, +(q.get('page') || 1)), limit = Math.min(100, Math.max(1, +(q.get('limit') || 20)));
    if (!Number.isFinite(page) || !Number.isFinite(limit)) throw bad('page/limit harus angka', ['page', 'limit']);
    const all = kasus.filter(k => k.tahun === tahun && (!pf || pf.includes(k.id_polsek)) && (!jf || jf.includes(k.id_jenis))).sort((a, b) => a.id_kasus - b.id_kasus);
    const data = all.slice((page - 1) * limit, page * limit).map(k => ({
      id_kasus: k.id_kasus, id_polsek: k.id_polsek, nama_polsek: polsekById(k.id_polsek).nama_polsek,
      id_jenis: k.id_jenis, nama_jenis: jenisById(k.id_jenis).nama_jenis, tahun: k.tahun, jumlah: k.jumlah }));
    return send(res, 200, { page, limit, total_data: all.length, data });
  }
  if (m === 'GET' && p === '/api/statistik') {
    const tahun = tahunParam(q), top = Math.max(1, +(q.get('top') || 4));
    const rp = rekap(tahun, null), total = rp.reduce((a, x) => a + x.total_kasus, 0);
    const perJenis = jenis.map(j => ({ ...j, jumlah: kasus.filter(k => k.tahun === tahun && k.id_jenis === j.id_jenis).reduce((a, k) => a + k.jumlah, 0) }))
      .sort((a, b) => b.jumlah - a.jumlah || a.id_jenis - b.id_jenis);
    const sorted = [...rp].sort((a, b) => b.total_kasus - a.total_kasus || a.id_polsek - b.id_polsek);
    const ringkas = x => ({ id_polsek: x.id_polsek, nama_polsek: x.nama_polsek, total_kasus: x.total_kasus });
    const topJ = perJenis.slice(0, top);
    return send(res, 200, {
      tahun, total_kasus: total, jumlah_polsek: polsek.length, jumlah_jenis: jenis.length,
      polsek_tertinggi: ringkas(sorted[0]), polsek_terendah: ringkas(sorted[sorted.length - 1]),
      distribusi_zona: { tinggi: rp.filter(x => x.kategori_zona === 'tinggi').length, sedang: rp.filter(x => x.kategori_zona === 'sedang').length, rendah: rp.filter(x => x.kategori_zona === 'rendah').length },
      top_jenis: topJ, persen_top_jenis: total ? +(topJ.reduce((a, x) => a + x.jumlah, 0) / total * 100).toFixed(1) : 0,
      per_polsek: sorted.map(x => ({ id_polsek: x.id_polsek, nama_polsek: x.nama_polsek, total_kasus: x.total_kasus, kategori_zona: x.kategori_zona })),
      per_jenis: perJenis });
  }
  if (m === 'GET' && p === '/api/statistik/tren') {
    const pf = intList(q, 'polsek'), jf = intList(q, 'jenis');
    const by = {};
    kasus.filter(k => (!pf || pf.includes(k.id_polsek)) && (!jf || jf.includes(k.id_jenis))).forEach(k => { by[k.tahun] = (by[k.tahun] || 0) + k.jumlah; });
    return send(res, 200, { data: Object.keys(by).sort().map(t => ({ tahun: +t, total_kasus: by[t] })) });
  }
  if (m === 'GET' && p === '/api/export') {
    const fmt = q.get('format');
    if (fmt !== 'csv') throw bad(fmt === 'pdf' ? 'Format pdf belum tersedia di mock server (cukup csv)' : 'Parameter format wajib diisi: csv', ['format']);
    const tahun = tahunParam(q), jf = intList(q, 'jenis'), pf = intList(q, 'polsek');
    const rows = rekap(tahun, jf).filter(x => !pf || pf.includes(x.id_polsek));
    const csv = 'id_polsek,nama_polsek,tahun,total_kasus,kategori_zona\n' + rows.map(x => [x.id_polsek, x.nama_polsek, x.tahun, x.total_kasus, x.kategori_zona].join(',')).join('\n') + '\n';
    res.writeHead(200, { ...CORS, 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': `attachment; filename="rekap_${tahun}.csv"` });
    return res.end(csv);
  }

  // ----- auth -----
  if (m === 'POST' && p === '/api/auth/login') {
    const b = await jsonBody(req);
    const us = USERS[b.username];
    if (!us || us.password !== b.password) throw new ApiError(401, 'TIDAK_TERAUTENTIKASI', 'Username atau password salah');
    return send(res, 200, { token: `mock-${b.username}`, tipe: 'Bearer', berlaku_detik: 86400, pengguna: { id_pengguna: us.id_pengguna, username: b.username, peran: us.peran } });
  }
  if (m === 'GET' && p === '/api/auth/me') { const a = auth(req); return send(res, 200, { id_pengguna: a.id_pengguna, username: a.username, peran: a.peran }); }

  // ----- admin: CRUD kasus & impor -----
  if (m === 'POST' && p === '/api/kasus') {
    auth(req);
    const b = await jsonBody(req), err = [];
    if (!polsekById(b.id_polsek)) err.push('id_polsek');
    if (!jenisById(b.id_jenis)) err.push('id_jenis');
    if (!Number.isInteger(b.tahun)) err.push('tahun');
    if (!Number.isInteger(b.jumlah) || b.jumlah < 0) err.push('jumlah');
    if (err.length) throw bad('Body tidak valid', err);
    if (kasus.some(k => k.id_polsek === b.id_polsek && k.id_jenis === b.id_jenis && k.tahun === b.tahun)) throw new ApiError(409, 'DATA_SUDAH_ADA', 'Kombinasi polsek+jenis+tahun sudah ada');
    const k = { id_kasus: nextId++, id_polsek: b.id_polsek, id_jenis: b.id_jenis, tahun: b.tahun, jumlah: b.jumlah };
    kasus.push(k);
    return send(res, 201, k);
  }
  if ((m === 'PUT' || m === 'DELETE') && (r = p.match(/^\/api\/kasus\/(\d+)$/))) {
    auth(req, m === 'DELETE' ? 'admin' : undefined);
    const k = kasus.find(x => x.id_kasus === +r[1]);
    if (!k) throw new ApiError(404, 'TIDAK_DITEMUKAN', `Kasus dengan id ${r[1]} tidak ditemukan`);
    if (m === 'DELETE') { kasus = kasus.filter(x => x !== k); res.writeHead(204, CORS); return res.end(); }
    const b = await jsonBody(req);
    if (!Number.isInteger(b.jumlah) || b.jumlah < 0) throw bad('Body tidak valid', ['jumlah']);
    k.jumlah = b.jumlah;
    return send(res, 200, k);
  }
  if (m === 'POST' && p === '/api/import/csv') {
    auth(req); await readBody(req);
    return send(res, 200, { tahun: 2024, baris_dibaca: 27, baris_valid: 27, total_kasus: 1163, peringatan: ['Mock server: berkas tidak diproses/disimpan'], disimpan: false });
  }
  if (m === 'POST' && p === '/api/_reset') { kasus = kasusAwal.map(k => ({ ...k })); nextId = Math.max(...kasus.map(k => k.id_kasus)) + 1; return send(res, 200, { reset: true }); }

  throw new ApiError(404, 'TIDAK_DITEMUKAN', `Endpoint ${m} ${p} tidak ada`);
}

const CORS = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'Authorization, Content-Type', 'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS' };
function send(res, status, obj) { res.writeHead(status, { ...CORS, 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(obj)); }

http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, CORS); return res.end(); }
  const t0 = Date.now();
  try { await handle(req, res, new URL(req.url, 'http://x')); }
  catch (e) {
    if (e instanceof ApiError) send(res, e.status, { error: { kode: e.kode, pesan: e.message, detail: e.detail } });
    else { console.error(e); send(res, 500, { error: { kode: 'KESALAHAN_SERVER', pesan: 'Kesalahan tak terduga', detail: [] } }); }
  }
  console.log(`${req.method} ${req.url} -> ${res.statusCode} (${Date.now() - t0} ms)`);
}).listen(PORT, () => console.log(`Mock API jalan di http://localhost:${PORT}/api`));
