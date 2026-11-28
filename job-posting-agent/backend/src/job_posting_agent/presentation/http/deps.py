"""ルートが使う依存。利用者を決めるのは、HTTP ではここ（current_user）だけ。

必要なもの（サービス、Authenticator、上限）は main.py が app.state に入れる。
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from ...application.interfaces import Authenticator
from ...application.services import HttpServices
from ...domain.models import UserId

CSRF_HEADER = "x-requested-with"


@dataclass(frozen=True)
class HttpContext:
    """main.py が app.state.http に入れるもの。"""

    services: HttpServices
    authenticator: Authenticator
    # 添付ファイルをどこまで読むか。上限を超えたかどうかの判断はサービスが行う
    upload_read_limit: int


def http_context(request: Request) -> HttpContext:
    ctx: HttpContext = request.app.state.http
    return ctx


Context = Annotated[HttpContext, Depends(http_context)]


async def current_user(request: Request, ctx: Context) -> UserId:
    return await ctx.authenticator.user_id(request.headers)


User = Annotated[UserId, Depends(current_user)]


def require_csrf_header(request: Request) -> None:
    # 独自ヘッダーは、他のサイトのフォームやリンクからは付けられない
    if request.headers.get(CSRF_HEADER) != "fetch":
        raise HTTPException(status_code=403, detail="不正なリクエストです")
