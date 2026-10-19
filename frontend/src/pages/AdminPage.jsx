// Halaman admin: tabel data kasus + form tambah/ubah + impor CSV.
// TODO task 32 (butuh endpoint CRUD & autentikasi dari Monica: task 25 & 26).
export default function AdminPage() {
  return (
    <>
      <h1 className="h3">Panel Admin</h1>
      <div className="row g-3">
        <div className="col-12">
          <div className="todo-box">Tabel data kasus + tombol Tambah / Ubah / Hapus (task 32)</div>
        </div>
        <div className="col-12 col-lg-6">
          <div className="todo-box">Form tambah / ubah data (task 32)</div>
        </div>
        <div className="col-12 col-lg-6">
          <div className="todo-box">Impor rekap CSV (task 32)</div>
        </div>
      </div>
    </>
  );
}
