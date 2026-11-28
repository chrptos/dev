"""利用者の特定（Authenticator の実装）。

本番では、IAP が付ける署名付きヘッダー（x-goog-iap-jwt-assertion）を検証して
メールアドレスを取り出す。x-goog-authenticated-user-email ヘッダーは偽装できるので使わない。
"""

import asyncio
import time
from collections.abc import Mapping

import httpx
from google.auth import jwt

from ..domain.errors import Unauthenticated
from ..domain.models import UserId

IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"
IAP_ISSUER = "https://cloud.google.com/iap"
IAP_HEADER = "x-goog-iap-jwt-assertion"
CERTS_TTL_SECONDS = 3600


class IapAuthenticator:
    def __init__(self, audience: str, certs_url: str = IAP_CERTS_URL) -> None:
        if not audience:
            raise RuntimeError("AUTH_MODE=iap では IAP_AUDIENCE の設定が必要です")
        self._audience = audience
        self._certs_url = certs_url
        self._certs: dict[str, str] | None = None
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()

    async def _get_certs(self) -> dict[str, str]:
        if self._certs is None or time.monotonic() - self._fetched_at > CERTS_TTL_SECONDS:
            async with self._lock:
                if self._certs is None or time.monotonic() - self._fetched_at > CERTS_TTL_SECONDS:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.get(self._certs_url)
                        resp.raise_for_status()
                        self._certs = resp.json()
                        self._fetched_at = time.monotonic()
        if self._certs is None:
            raise Unauthenticated("IAP の公開鍵を取得できません")
        return self._certs

    async def user_id(self, headers: Mapping[str, str]) -> UserId:
        token = headers.get(IAP_HEADER)
        if not token:
            raise Unauthenticated("IAP を通していないリクエストです")
        certs = await self._get_certs()
        try:
            claims = jwt.decode(token, certs=certs, audience=self._audience)
        except Exception as e:
            raise Unauthenticated("IAP の署名を確認できません") from e
        if claims.get("iss") != IAP_ISSUER:
            raise Unauthenticated("IAP が発行したものではありません")
        email = claims.get("email")
        if not isinstance(email, str) or "@" not in email:
            raise Unauthenticated("メールアドレスがありません")
        return UserId(email.lower())


class LocalAuthenticator:
    """手元での開発用。いつも同じ利用者として扱う。"""

    def __init__(self, user: str) -> None:
        self._user = UserId(user)

    async def user_id(self, headers: Mapping[str, str]) -> UserId:
        return self._user
