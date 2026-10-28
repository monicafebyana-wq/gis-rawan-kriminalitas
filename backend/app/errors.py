"""Format error seragam sesuai docs/api-contract.md:
   {"error": {"kode": "...", "pesan": "...", "detail": [...]}}"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, kode: str, pesan: str, detail: list | None = None, headers: dict | None = None):
        self.status, self.kode, self.pesan, self.detail, self.headers = status, kode, pesan, detail or [], headers


def tidak_ditemukan(pesan: str) -> ApiError:
    return ApiError(404, "TIDAK_DITEMUKAN", pesan)


def validasi_gagal(pesan: str, detail: list | None = None) -> ApiError:
    return ApiError(400, "VALIDASI_GAGAL", pesan, detail)


def belum_diimplementasi(nama: str) -> ApiError:
    return ApiError(501, "BELUM_DIIMPLEMENTASI", f"Endpoint {nama} belum dikerjakan")


def _respons(status: int, kode: str, pesan: str, detail: list, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"kode": kode, "pesan": pesan, "detail": detail}}, headers=headers)


def daftar_handler(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, e: ApiError):
        return _respons(e.status, e.kode, e.pesan, e.detail, e.headers)

    @app.exception_handler(RequestValidationError)
    async def _validasi(_: Request, e: RequestValidationError):
        # nama field yang bermasalah (tanpa 'query'/'body' di depan)
        field = [str(err["loc"][-1]) for err in e.errors() if err.get("loc")]
        return _respons(400, "VALIDASI_GAGAL", "Parameter atau body tidak valid", field)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        kode = {404: "TIDAK_DITEMUKAN", 401: "TIDAK_TERAUTENTIKASI", 403: "TIDAK_DIIZINKAN"}.get(e.status_code, "KESALAHAN_SERVER")
        pesan = "Endpoint tidak ditemukan" if (e.status_code == 404 and e.detail == "Not Found") else str(e.detail)
        return _respons(e.status_code, kode, pesan, [])

    @app.exception_handler(Exception)
    async def _lainnya(_: Request, e: Exception):
        import logging
        logging.getLogger("uvicorn.error").exception("Kesalahan tak terduga", exc_info=e)
        return _respons(500, "KESALAHAN_SERVER", "Kesalahan tak terduga di server", [])
