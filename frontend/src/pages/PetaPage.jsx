import { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../api.js';

// Halaman Peta (/peta): bilah filter di atas, peta besar di kiri, panel Kontrol Layer + Keterangan Zona di kanan.
// Poligon diwarnai menurut zona; klik poligon untuk melihat rincian jenis kejahatan.

const WARNA = { tinggi: '#FF3131', sedang: '#FFC800', rendah: '#20A99B' };
const LABEL = { tinggi: 'Tinggi', sedang: 'Sedang', rendah: 'Rendah' };
const PUSAT_AWAL = [-7.05, 107.55]; // Kab. Bandung
// Pilihan peta dasar (Kontrol Layer).
const PETA_DASAR = {
  osm: {
    nama: 'Peta Jalan',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  satelit: {
    nama: 'Citra Satelit',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
  },
  topo: {
    nama: 'Topografi',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap, &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
  },
};
const FILTER_AWAL = { tahun: '', jenis: '', polsek: '', zona: ['tinggi', 'sedang', 'rendah'] };

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Ubah pilihan filter di layar menjadi parameter API.
function keParams(f) {
  const p = { tahun: f.tahun, jenis: f.jenis, polsek: f.polsek };
  if (f.zona.length < 3) p.zona = f.zona.join(',');
  return p;
}

// Pas-kan tampilan peta ke semua poligon yang sedang tampil.
function PasKanPeta({ data }) {
  const map = useMap();
  useEffect(() => {
    if (!data || !data.features.length) return;
    const batas = L.geoJSON(data).getBounds();
    if (batas.isValid()) map.fitBounds(batas, { padding: [20, 20] });
  }, [data, map]);
  return null;
}

// Isi popup: rincian jenis kejahatan satu Polsek.
function isiPopup(d) {
  const baris = d.rincian_jenis
    .map((r) => `<tr><td>${esc(r.nama_jenis)}</td><td class="text-end fw-semibold">${r.jumlah}</td></tr>`)
    .join('');
  return `
    <div class="popup-polsek">
      <div class="fw-bold fs-6">Polsek ${esc(d.nama_polsek)}</div>
      <div class="mb-2">
        <span class="badge" style="background:${WARNA[d.kategori_zona]};color:${d.kategori_zona === 'sedang' ? '#000' : '#fff'}">
          Zona ${LABEL[d.kategori_zona]}</span>
        <span class="ms-1">${d.total_kasus} kasus (${d.tahun})</span>
      </div>
      <table class="table table-sm mb-0"><tbody>${baris}</tbody></table>
    </div>`;
}

export default function PetaPage() {
  const [daftarTahun, setDaftarTahun] = useState([]);
  const [daftarJenis, setDaftarJenis] = useState([]);
  const [daftarPolsek, setDaftarPolsek] = useState([]);

  const [form, setForm] = useState(FILTER_AWAL); // pilihan di panel (belum diterapkan)
  const [terapkan, setTerapkan] = useState(FILTER_AWAL); // filter yang dipakai peta
  const [data, setData] = useState(null);
  const [status, setStatus] = useState('memuat'); // memuat | ok | gagal
  const [pesanGagal, setPesanGagal] = useState('');
  const [filterTerbuka, setFilterTerbuka] = useState(false); // hanya untuk layar HP
  const [dasar, setDasar] = useState('osm'); // peta dasar yang dipilih
  const [opasitas, setOpasitas] = useState(70); // kepekatan warna zona, 20-100 (%)
  const opasitasRef = useRef(0.7); // dibaca gayaPoligon, supaya tidak ketinggalan nilai lama
  const geoRef = useRef(null);

  // Sekali di awal: isi pilihan filter.
  useEffect(() => {
    Promise.all([api.tahun(), api.jenis(), api.polsek()])
      .then(([t, j, p]) => {
        setDaftarTahun(t.data);
        setDaftarJenis(j.data);
        setDaftarPolsek(
          p.features
            .map((f) => ({ id: f.properties.id_polsek, nama: f.properties.nama_polsek }))
            .sort((a, b) => a.nama.localeCompare(b.nama))
        );
        setForm((f) => ({ ...f, tahun: String(t.terbaru) }));
        setTerapkan((f) => ({ ...f, tahun: String(t.terbaru) }));
      })
      .catch(() => {});
  }, []);

  // Setiap filter diterapkan: ambil data peta.
  useEffect(() => {
    setStatus('memuat');
    api
      .polsek(keParams(terapkan))
      .then((fc) => {
        setData(fc);
        setStatus('ok');
      })
      .catch((e) => {
        setPesanGagal(e.message);
        setStatus('gagal');
      });
  }, [terapkan]);

  const hitungZona = useMemo(() => {
    const h = { tinggi: 0, sedang: 0, rendah: 0 };
    if (data) data.features.forEach((f) => { h[f.properties.kategori_zona] += 1; });
    return h;
  }, [data]);

  const totalKasus = useMemo(
    () => (data ? data.features.reduce((a, f) => a + f.properties.total_kasus, 0) : 0),
    [data]
  );

  function ubahZona(z) {
    setForm((f) => ({
      ...f,
      zona: f.zona.includes(z) ? f.zona.filter((x) => x !== z) : [...f.zona, z],
    }));
  }

  function tampilkan(e) {
    e.preventDefault();
    if (form.zona.length === 0) return;
    setTerapkan(form);
    setFilterTerbuka(false);
  }

  function aturUlang() {
    const awal = { ...FILTER_AWAL, tahun: form.tahun };
    setForm(awal);
    setTerapkan(awal);
  }

  const gayaPoligon = (feature) => ({
    color: '#ffffff',
    weight: 1.5,
    fillColor: WARNA[feature.properties.kategori_zona] || '#9aa3af',
    fillOpacity: opasitasRef.current,
  });

  function ubahOpasitas(nilai) {
    const n = Number(nilai);
    setOpasitas(n);
    opasitasRef.current = n / 100;
    if (geoRef.current) geoRef.current.setStyle(gayaPoligon);
  }

  function tiapFitur(feature, layer) {
    const p = feature.properties;
    layer.bindTooltip(`${p.nama_polsek} · ${p.total_kasus} kasus`, { sticky: true });
    layer.bindPopup('<div class="text-secondary">Memuat rincian…</div>', { maxWidth: 300 });
    layer.on({
      mouseover: () => layer.setStyle({ weight: 3, fillOpacity: 0.85 }),
      mouseout: () => layer.setStyle(gayaPoligon(feature)),
      click: () => {
        api
          .polsekDetail(p.id_polsek, { tahun: terapkan.tahun })
          .then((d) => layer.setPopupContent(isiPopup(d)))
          .catch(() => layer.setPopupContent('<div class="text-danger">Rincian gagal dimuat.</div>'));
      },
    });
  }

  return (
    <>
      <div className="mb-3">
        <h1 className="h3 mb-1">Peta Rawan Kriminalitas Kabupaten Bandung</h1>
        <p className="text-secondary mb-0">
          Warna wilayah menunjukkan tingkat kerawanan. Klik wilayah di peta untuk melihat rincian kasus.
        </p>
      </div>

      {/* Bilah filter */}
      <button
        type="button"
        className="btn btn-primary w-100 d-lg-none mb-2"
        onClick={() => setFilterTerbuka((v) => !v)}
        aria-expanded={filterTerbuka}
      >
        {filterTerbuka ? 'Tutup pencarian' : 'Cari & saring data'}
      </button>

      <form className={`card mb-3 ${filterTerbuka ? '' : 'd-none'} d-lg-block`} onSubmit={tampilkan}>
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-6 col-lg-2">
              <label className="form-label fw-semibold" htmlFor="f-tahun">Tahun</label>
              <select
                id="f-tahun"
                className="form-select"
                value={form.tahun}
                onChange={(e) => setForm({ ...form, tahun: e.target.value })}
              >
                {daftarTahun.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="col-6 col-lg-3">
              <label className="form-label fw-semibold" htmlFor="f-jenis">Jenis kejahatan</label>
              <select
                id="f-jenis"
                className="form-select"
                value={form.jenis}
                onChange={(e) => setForm({ ...form, jenis: e.target.value })}
              >
                <option value="">Semua jenis</option>
                {daftarJenis.map((j) => <option key={j.id_jenis} value={j.id_jenis}>{j.nama_jenis}</option>)}
              </select>
            </div>

            <div className="col-12 col-lg-3">
              <label className="form-label fw-semibold" htmlFor="f-polsek">Wilayah (Polsek)</label>
              <select
                id="f-polsek"
                className="form-select"
                value={form.polsek}
                onChange={(e) => setForm({ ...form, polsek: e.target.value })}
              >
                <option value="">Semua wilayah</option>
                {daftarPolsek.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
              </select>
            </div>

            <div className="col-12 col-lg-4">
              <div className="fw-semibold mb-1">Tingkat kerawanan</div>
              <div className="d-flex flex-wrap column-gap-3">
                {[
                  ['tinggi', 'Tinggi'],
                  ['sedang', 'Sedang'],
                  ['rendah', 'Rendah'],
                ].map(([z, teks]) => (
                  <div className="form-check" key={z}>
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id={`z-${z}`}
                      checked={form.zona.includes(z)}
                      onChange={() => ubahZona(z)}
                    />
                    <label className="form-check-label" htmlFor={`z-${z}`}>
                      <span className={`dot dot-${z}`} /> {teks}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {form.zona.length === 0 && (
            <div className="text-danger small mt-2">Pilih minimal satu tingkat kerawanan.</div>
          )}

          <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-3">
            <span className="small text-secondary">
              Warna zona dihitung dari total semua jenis kejahatan, walaupun kamu memilih satu jenis saja.
            </span>
            <div className="d-flex gap-2">
              <button className="btn btn-outline-secondary" type="button" onClick={aturUlang}>
                Atur ulang
              </button>
              <button className="btn btn-primary" type="submit" disabled={form.zona.length === 0}>
                Terapkan filter
              </button>
            </div>
          </div>
        </div>
      </form>

      {status === 'gagal' && (
        <div className="alert alert-danger py-2" role="alert">
          Data belum bisa dimuat ({pesanGagal}). Pastikan backend sudah jalan di <code>http://localhost:3000</code>.
        </div>
      )}
      {status === 'ok' && data && (
        <div className="small text-secondary mb-2">
          Menampilkan <strong>{data.features.length}</strong> wilayah · total{' '}
          <strong>{totalKasus}</strong> kasus
          {data.features.length === 0 && ' — tidak ada wilayah yang cocok dengan pilihanmu.'}
        </div>
      )}

      <div className="row g-3">
        {/* Peta */}
        <div className="col-12 col-lg-9 d-flex flex-column">
          <div className="peta-wrap">
            <MapContainer center={PUSAT_AWAL} zoom={10} scrollWheelZoom className="peta-area">
              <TileLayer
                key={dasar}
                attribution={PETA_DASAR[dasar].attribution}
                url={PETA_DASAR[dasar].url}
              />
              {data && (
                <GeoJSON
                  key={JSON.stringify(terapkan) + data.features.length + totalKasus}
                  ref={geoRef}
                  data={data}
                  style={gayaPoligon}
                  onEachFeature={tiapFitur}
                />
              )}
              <PasKanPeta data={data} />
            </MapContainer>

            {status === 'memuat' && <div className="peta-memuat">Memuat peta…</div>}
          </div>
        </div>

        {/* Panel samping: Kontrol Layer + Keterangan Zona */}
        <div className="col-12 col-lg-3 panel-samping d-flex flex-column gap-3">
          <div className="card">
            <div className="card-body">
              <h2>Kontrol layer</h2>

              <div className="fw-semibold small mb-1">Peta dasar</div>
              {Object.entries(PETA_DASAR).map(([k, v]) => (
                <div className="form-check" key={k}>
                  <input
                    className="form-check-input"
                    type="radio"
                    name="peta-dasar"
                    id={`dasar-${k}`}
                    checked={dasar === k}
                    onChange={() => setDasar(k)}
                  />
                  <label className="form-check-label" htmlFor={`dasar-${k}`}>{v.nama}</label>
                </div>
              ))}

              <label className="form-label fw-semibold small mt-3 mb-0" htmlFor="opasitas">
                Kepekatan warna zona: {opasitas}%
              </label>
              <input
                id="opasitas"
                type="range"
                className="form-range"
                min="20"
                max="100"
                step="5"
                value={opasitas}
                onChange={(e) => ubahOpasitas(e.target.value)}
              />
            </div>
          </div>

          <div className="card" aria-label="Keterangan zona kerawanan">
            <div className="card-body">
              <h2>Keterangan zona</h2>
              {[
                ['tinggi', 'Tinggi', '60 kasus atau lebih'],
                ['sedang', 'Sedang', '30 sampai 59 kasus'],
                ['rendah', 'Rendah', 'di bawah 30 kasus'],
              ].map(([z, nama, ket]) => (
                <div className="baris-zona" key={z}>
                  <span>
                    <span className={`dot dot-${z}`} /> <strong>{nama}</strong>
                    <span className="d-block small text-secondary ms-4">{ket}</span>
                  </span>
                  <span className="fw-semibold">{hitungZona[z]} wilayah</span>
                </div>
              ))}
              <div className="small text-secondary mt-2">
                Total {totalKasus} kasus di {data ? data.features.length : 0} wilayah.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="small text-secondary mt-2">
        Sumber data: rekap kriminalitas (27 Polsek). Batas wilayah mengikuti batas kecamatan (GADM).
      </div>
    </>
  );
}
