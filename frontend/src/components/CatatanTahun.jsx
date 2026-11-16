// Peringatan per tahun data (mis. "Data tahun 2025 adalah SIMULASI ..."), dari GET /api/tahun -> catatan.
// Tidak menampilkan apa pun bila tahun itu tidak punya catatan.
export default function CatatanTahun({ catatan, tahun, className = 'mb-2' }) {
  const teks = catatan && tahun ? catatan[String(tahun)] : null;
  if (!teks) return null;
  return (
    <div className={`alert alert-warning py-2 small ${className}`} role="note">
      <strong>Catatan data {tahun}:</strong> {teks}
    </div>
  );
}
