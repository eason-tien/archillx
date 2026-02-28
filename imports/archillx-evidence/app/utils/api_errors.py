from __future__ import annotations

from fastapi import HTTPException


class AppHTTPError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status_code, detail={
            "code": code,
            "message": message,
            "details": details or {},
        })


def bad_request(code: str, message: str, details: dict | None = None) -> AppHTTPError:
    return AppHTTPError(400, code, message, details)


def not_found(code: str, message: str, details: dict | None = None) -> AppHTTPError:
    return AppHTTPError(404, code, message, details)


def service_unavailable(code: str, message: str, details: dict | None = None) -> AppHTTPError:
    return AppHTTPError(503, code, message, details)


def internal_error(code: str, message: str, details: dict | None = None) -> AppHTTPError:
    return AppHTTPError(500, code, message, details)
