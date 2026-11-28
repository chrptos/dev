"""URL 取得で、社内や手元のアドレスに接続しないことを確かめる。ネットワークには出ない。"""

import httpx
import pytest

from job_posting_agent.domain.errors import FetchFailed
from job_posting_agent.infrastructure import web_fetcher
from job_posting_agent.infrastructure.web_fetcher import (
    SafeWebPageFetcher,
    html_to_text,
    validate_url,
)

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "https://user:pass@example.com/",
        "https:///nohost",
        "http://example.com:99999/",
    ],
)
def test_rejects_bad_urls(url: str) -> None:
    with pytest.raises(FetchFailed):
        validate_url(url)


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "localhost",
        "10.0.0.1",
        "172.16.5.4",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "::1",
        "fd00::1",
        "::ffff:127.0.0.1",
    ],
)
async def test_rejects_non_public_hosts(host: str) -> None:
    with pytest.raises(FetchFailed):
        await web_fetcher.check_host_is_public(host, 443)


def test_html_to_text_drops_scripts_and_keeps_title() -> None:
    title, text = html_to_text(
        "<html><head><title>求人A</title><style>x{}</style></head>"
        "<body><script>alert(1)</script><h1>職種</h1><p>必須:  Go</p></body></html>"
    )
    assert title == "求人A"
    assert "alert" not in text and "x{}" not in text
    assert text.splitlines()[0] == "職種"
    assert "必須: Go" in text


async def test_redirect_to_private_address_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    checked: list[str] = []

    async def fake_check(host: str, port: int) -> None:
        checked.append(host)
        if host != "jobs.example.com":
            raise FetchFailed("社内や手元のアドレスには接続できません")

    monkeypatch.setattr(web_fetcher, "check_host_is_public", fake_check)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://169.254.169.254/computeMetadata/"})

    fetcher = SafeWebPageFetcher(max_bytes=1000, timeout=5, transport=httpx.MockTransport(handler))
    with pytest.raises(FetchFailed):
        await fetcher.fetch("https://jobs.example.com/1")
    assert checked == ["jobs.example.com", "169.254.169.254"]


async def test_fetch_truncates_rejects_pdf_and_hides_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def ok(host: str, port: int) -> None:
        return None

    monkeypatch.setattr(web_fetcher, "check_host_is_public", ok)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/pdf":
            return httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
        if request.url.path == "/boom":
            raise httpx.ConnectError("connection refused")
        return httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=("<p>" + "あ" * 5000 + "</p>").encode(),
        )

    fetcher = SafeWebPageFetcher(max_bytes=3000, timeout=5, transport=httpx.MockTransport(handler))
    page = await fetcher.fetch("https://e.com/")
    assert page.truncated is True
    assert len(page.text.encode()) <= 3000

    with pytest.raises(FetchFailed, match="PDF"):
        await fetcher.fetch("https://e.com/pdf")
    # 想定外のエラーも、利用者に見せてよい文の FetchFailed にする
    with pytest.raises(FetchFailed, match="時間をおいて"):
        await fetcher.fetch("https://e.com/boom")
