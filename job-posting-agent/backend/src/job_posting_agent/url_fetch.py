"""求人ページの URL を安全に取得し、本文のテキストを取り出す。

社内や手元のサービスを覗く踏み台にされないよう、グローバルなアドレス以外には接続しない。
リダイレクト先も毎回確認する。

残るリスク: 名前解決の結果を確認してから接続するまでの間に DNS の応答が変わる
（DNS リバインディング）と、確認をすり抜けられる。Cloud Run のメタデータサーバーは
Metadata-Flavor ヘッダーがないと応答しないため、その影響は小さい。
"""

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_REDIRECTS = 5
MAX_TEXT_CHARS = 30_000
USER_AGENT = "job-posting-agent/0.1"


class UrlFetchError(ValueError):
    """利用者に伝えてよい、取得できなかった理由。"""


@dataclass
class FetchedPage:
    url: str
    title: str | None
    text: str
    truncated: bool


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def validate_url(url: str) -> tuple[str, int]:
    """形式だけを確認し、(ホスト名, ポート) を返す。"""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UrlFetchError("http か https の URL だけを取得できます")
    if parts.username or parts.password:
        raise UrlFetchError("ユーザー名やパスワードを含む URL は取得できません")
    if not parts.hostname:
        raise UrlFetchError("URL にホスト名がありません")
    try:
        port = parts.port or (443 if parts.scheme == "https" else 80)
    except ValueError as e:
        raise UrlFetchError("URL のポート番号が正しくありません") from e
    return parts.hostname, port


async def check_host_is_public(host: str, port: int) -> None:
    """名前解決したすべてのアドレスがグローバルなアドレスであることを確認する。"""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UrlFetchError(f"ホスト名を解決できません: {host}") from e
    if not infos:
        raise UrlFetchError(f"ホスト名を解決できません: {host}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not _is_public_ip(ip):
            raise UrlFetchError("社内や手元のアドレスには接続できません")


class _TextExtractor(HTMLParser):
    _SKIP = frozenset({"script", "style", "noscript", "svg", "template", "head"})
    _BLOCK = frozenset(
        {
            "p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
            "section", "article", "dt", "dd", "table", "ul", "ol",
        }
    )  # fmt: skip

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        elif tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = ((self.title or "") + data).strip() or None
        elif self._skip_depth == 0:
            self._chunks.append(data)

    def text(self) -> str:
        raw = "".join(self._chunks)
        lines = (re.sub(r"[ \t　]+", " ", line).strip() for line in raw.splitlines())
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def html_to_text(html: str) -> tuple[str | None, str]:
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    return parser.title, parser.text()


async def fetch_page(
    url: str,
    *,
    max_bytes: int,
    timeout: float,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FetchedPage:
    current = url
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
        trust_env=False,
        transport=transport,
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            host, port = validate_url(current)
            await check_host_is_public(host, port)
            async with client.stream("GET", current) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise UrlFetchError("リダイレクト先がありません")
                    current = urljoin(current, location)
                    continue
                if resp.status_code != 200:
                    raise UrlFetchError(f"ページを取得できませんでした（HTTP {resp.status_code}）")
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type == "application/pdf":
                    raise UrlFetchError(
                        "この URL は PDF です。ダウンロードして、チャットに添付してください"
                    )
                if content_type not in ("text/html", "application/xhtml+xml", "text/plain"):
                    raise UrlFetchError(f"このページの形式には対応していません（{content_type}）")

                body = bytearray()
                truncated = False
                async for chunk in resp.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        del body[max_bytes:]
                        truncated = True
                        break
                charset = resp.charset_encoding or "utf-8"
                decoded = bytes(body).decode(charset, errors="replace")

            if content_type == "text/plain":
                title, text = None, decoded.strip()
            else:
                title, text = html_to_text(decoded)
            if len(text) > MAX_TEXT_CHARS:
                text = text[:MAX_TEXT_CHARS]
                truncated = True
            return FetchedPage(url=current, title=title, text=text, truncated=truncated)
    raise UrlFetchError("リダイレクトが多すぎます")
