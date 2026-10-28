"""Pembatas percobaan login GAGAL (brute force). Disimpan di memori proses -> cukup untuk 1 worker uvicorn;
bila nanti memakai banyak worker/server, pindahkan ke Redis.

  periksa(ip, username)      -> raise 429 bila sudah terlalu banyak gagal (dipanggil SEBELUM cek password)
  catat_gagal(ip, username)  -> dipanggil saat login gagal
  reset(ip, username)        -> dipanggil saat login berhasil
Dua batas: per (IP + username) = settings.login_maks_gagal, dan per IP (semua username) = settings.login_maks_gagal_ip.
"""
import threading
import time
from collections import defaultdict, deque

from app.config import settings
from app.errors import ApiError

_kunci = threading.Lock()
_gagal: dict[str, deque[float]] = defaultdict(deque)


def _kunci_user(ip: str, username: str) -> str:
    return f"u|{ip}|{username.lower()}"


def _kunci_ip(ip: str) -> str:
    return f"ip|{ip}"


def _aktif(kunci: str, sekarang: float) -> deque[float]:
    d = _gagal[kunci]
    while d and d[0] <= sekarang - settings.login_jendela_detik:
        d.popleft()
    if not d:
        del _gagal[kunci]
        return _gagal[kunci]                 # deque kosong baru (defaultdict)
    return d


def periksa(ip: str, username: str) -> None:
    sekarang = time.monotonic()
    with _kunci:
        for kunci, batas in ((_kunci_user(ip, username), settings.login_maks_gagal), (_kunci_ip(ip), settings.login_maks_gagal_ip)):
            d = _aktif(kunci, sekarang)
            if len(d) >= batas:
                tunggu = int(d[0] + settings.login_jendela_detik - sekarang) + 1
                raise ApiError(429, "TERLALU_BANYAK_PERCOBAAN",
                               f"Terlalu banyak percobaan login gagal. Coba lagi dalam {tunggu} detik.",
                               headers={"Retry-After": str(tunggu)})


def catat_gagal(ip: str, username: str) -> None:
    sekarang = time.monotonic()
    with _kunci:
        _gagal[_kunci_user(ip, username)].append(sekarang)
        _gagal[_kunci_ip(ip)].append(sekarang)
        if len(_gagal) > 10_000:             # cegah memori membengkak oleh serangan dengan banyak username acak
            for k in list(_gagal):
                _aktif(k, sekarang)


def reset(ip: str, username: str) -> None:
    with _kunci:
        _gagal.pop(_kunci_user(ip, username), None)


def reset_semua() -> None:
    with _kunci:
        _gagal.clear()
