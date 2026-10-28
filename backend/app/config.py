"""Konfigurasi aplikasi. Nilai dibaca dari environment / file .env di ROOT repo (lihat .env.example)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]   # backend/app/config.py -> root repo


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # Database (sama dengan yang dipakai docker-compose.yml)
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "gis_kriminalitas"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_pool_min: int = 1
    db_pool_max: int = 5
    db_timeout: float = 5.0          # detik menunggu koneksi dari pool

    # CORS
    cors_origins: str = "*"          # pisahkan koma, mis. "http://localhost:5500,http://127.0.0.1:5500"

    # Autentikasi
    jwt_secret: str = "ganti_dengan_string_acak"
    jwt_berlaku_detik: int = 86400
    bcrypt_rounds: int = 12          # makin tinggi makin aman tapi makin lambat (tes memakai 4)
    login_maks_gagal: int = 5        # login gagal per (IP + username) sebelum diblokir sementara (HTTP 429)
    login_maks_gagal_ip: int = 30    # login gagal per IP (semua username)
    login_jendela_detik: int = 900   # lama hitungan & blokir (15 menit)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
