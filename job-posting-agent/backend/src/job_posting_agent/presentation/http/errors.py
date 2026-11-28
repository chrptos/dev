"""ドメインのエラーを HTTP のレスポンスに変える。変換はここでだけ行う。"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ...domain.errors import (
    DomainError,
    FetchFailed,
    InvalidInput,
    NotFound,
    PayloadTooLarge,
    RateLimited,
    Unauthenticated,
    UnsupportedAttachment,
)

# 上から順に調べる（子クラスを親クラスより先に書く）
_STATUS: list[tuple[type[DomainError], int]] = [
    (Unauthenticated, 401),
    (NotFound, 404),
    (PayloadTooLarge, 413),
    (UnsupportedAttachment, 415),
    (InvalidInput, 400),
    (RateLimited, 429),
    (FetchFailed, 502),
]


def status_for(error: DomainError) -> int:
    for cls, status in _STATUS:
        if isinstance(error, cls):
            return status
    return 400


async def _handle(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101 - DomainError にだけ登録している
    status = status_for(exc)
    # ログインできない理由は利用者に見せない
    detail = "ログインが必要です" if status == 401 else exc.message
    return JSONResponse({"detail": detail}, status_code=status)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle)
