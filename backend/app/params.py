"""Helper parameter query yang dipakai banyak endpoint."""
from app.errors import validasi_gagal

ZONA_VALID = ("tinggi", "sedang", "rendah")


def daftar_int(nilai: str | None, nama: str) -> list[int] | None:
    """'1,16' -> [1, 16]. Kosong/None -> None (artinya: tanpa filter)."""
    if nilai is None or nilai.strip() == "":
        return None
    bagian = [s.strip() for s in nilai.split(",")]
    if not all(s.isdigit() for s in bagian):
        raise validasi_gagal(f"Parameter {nama} harus berupa angka dipisah koma", [nama])
    return [int(s) for s in bagian]


def daftar_zona(nilai: str | None) -> list[str] | None:
    if nilai is None or nilai.strip() == "":
        return None
    bagian = [s.strip() for s in nilai.split(",")]
    if any(s not in ZONA_VALID for s in bagian):
        raise validasi_gagal("Parameter zona harus tinggi/sedang/rendah", ["zona"])
    return bagian
