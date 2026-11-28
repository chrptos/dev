"""API を、偽のモデルを使った本物の Runner とセッション保存で通して確かめる。"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import pytest
from fastapi.testclient import TestClient

from job_posting_agent import repository
from job_posting_agent.agent import build_agent
from job_posting_agent.auth import AuthError
from job_posting_agent.config import Settings
from job_posting_agent.server import create_app

from .conftest import ScriptedLlm, call_reply, text_reply

HEADERS = {"X-Requested-With": "fetch"}


class HeaderAuth:
    """テスト用: x-test-user ヘッダーの値を利用者にする。"""

    async def user_id(self, headers: Any) -> str:
        user = headers.get("x-test-user")
        if not user:
            raise AuthError("no user")
        return str(user)


@pytest.fixture
def llm() -> ScriptedLlm:
    return ScriptedLlm()


def make_client(llm: ScriptedLlm, **settings: Any) -> TestClient:
    app = create_app(
        Settings(auth_mode="local", rate_limit_per_minute=3, **settings),
        agent=build_agent(llm),
        authenticator=HeaderAuth(),  # type: ignore[arg-type]
    )
    return TestClient(app)


@pytest.fixture
def client(llm: ScriptedLlm) -> Iterator[TestClient]:
    with make_client(llm) as c:
        yield c


def as_user(user: str) -> dict[str, str]:
    return {**HEADERS, "x-test-user": user}


def events(resp: Any) -> list[dict[str, Any]]:
    return [json.loads(line[6:]) for line in resp.text.split("\n\n") if line.startswith("data: ")]


def new_session(client: TestClient, user: str) -> str:
    resp = client.post("/api/sessions", headers=as_user(user))
    assert resp.status_code == 200
    return str(resp.json()["id"])


def test_requires_login(client: TestClient) -> None:
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/healthz").status_code == 200


def test_post_requires_csrf_header(client: TestClient) -> None:
    resp = client.post("/api/sessions", headers={"x-test-user": "a@x.com"})
    assert resp.status_code == 403


def test_chat_flow_saves_summary_for_the_logged_in_user(
    client: TestClient, llm: ScriptedLlm
) -> None:
    llm.script = [
        call_reply(
            "save_job_summary",
            {
                "summary": {
                    "company": "株式会社A",
                    "title": "SRE",
                    "source_type": "text",
                    "source_ref": "pasted",
                }
            },
        ),
        text_reply("まとめました。"),
    ]
    sid = new_session(client, "alice@x.com")
    resp = client.post(
        f"/api/sessions/{sid}/messages",
        headers=as_user("alice@x.com"),
        data={"text": "この求人票をまとめて: 株式会社A SRE"},
    )
    assert resp.status_code == 200
    evs = events(resp)
    assert {"type": "tool", "name": "save_job_summary"} in evs
    assert "".join(e["text"] for e in evs if e["type"] == "delta") == "まとめました。"
    assert evs[-1] == {"type": "done"}

    # ツールに渡った利用者は、ログインした本人
    saved = anyio.run(repository.list_summaries, "alice@x.com")
    assert [s["company"] for s in saved] == ["株式会社A"]
    assert anyio.run(repository.list_summaries, "bob@x.com") == []

    # 履歴とタイトル
    history = client.get(f"/api/sessions/{sid}", headers=as_user("alice@x.com")).json()
    assert [m["role"] for m in history["messages"]] == ["user", "agent"]
    sessions = client.get("/api/sessions", headers=as_user("alice@x.com")).json()
    assert sessions[0]["title"].startswith("この求人票をまとめて")


def test_other_users_session_is_not_found(client: TestClient, llm: ScriptedLlm) -> None:
    sid = new_session(client, "alice@x.com")
    bob = as_user("bob@x.com")
    assert client.get(f"/api/sessions/{sid}", headers=bob).status_code == 404
    resp = client.post(f"/api/sessions/{sid}/messages", headers=bob, data={"text": "hi"})
    assert resp.status_code == 404
    assert client.delete(f"/api/sessions/{sid}", headers=bob).status_code == 404
    assert client.get("/api/sessions", headers=bob).json() == []
    assert llm.requests == []


def test_pdf_is_passed_to_the_model(client: TestClient, llm: ScriptedLlm) -> None:
    llm.script = [text_reply("読みました")]
    sid = new_session(client, "alice@x.com")
    resp = client.post(
        f"/api/sessions/{sid}/messages",
        headers=as_user("alice@x.com"),
        data={"text": ""},
        files={"file": ("job.pdf", b"%PDF-1.7 dummy", "application/pdf")},
    )
    assert resp.status_code == 200
    parts = llm.requests[0].contents[-1].parts or []
    assert any(p.inline_data and p.inline_data.mime_type == "application/pdf" for p in parts)
    history = client.get(f"/api/sessions/{sid}", headers=as_user("alice@x.com")).json()
    assert history["messages"][0]["attachments"] == ["job.pdf"]


def test_non_pdf_upload_is_rejected(client: TestClient) -> None:
    sid = new_session(client, "alice@x.com")
    resp = client.post(
        f"/api/sessions/{sid}/messages",
        headers=as_user("alice@x.com"),
        data={"text": "x"},
        files={"file": ("a.pdf", b"<html>not pdf", "application/pdf")},
    )
    assert resp.status_code == 415


def test_rate_limit_is_per_user(client: TestClient, llm: ScriptedLlm) -> None:
    llm.script = [text_reply("ok") for _ in range(10)]
    alice = new_session(client, "alice@x.com")
    bob = new_session(client, "bob@x.com")
    codes = [
        client.post(
            f"/api/sessions/{alice}/messages", headers=as_user("alice@x.com"), data={"text": "hi"}
        ).status_code
        for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]
    resp = client.post(
        f"/api/sessions/{bob}/messages", headers=as_user("bob@x.com"), data={"text": "hi"}
    )
    assert resp.status_code == 200


def test_delete_session(client: TestClient) -> None:
    sid = new_session(client, "alice@x.com")
    assert client.delete(f"/api/sessions/{sid}", headers=as_user("alice@x.com")).status_code == 200
    assert client.get(f"/api/sessions/{sid}", headers=as_user("alice@x.com")).status_code == 404


def test_serves_frontend_build_without_hiding_api(llm: ScriptedLlm, tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    with make_client(llm, frontend_dist=str(tmp_path)) as c:
        assert "root" in c.get("/").text
        assert c.get("/assets/app.js").status_code == 200
        assert c.get("/api/sessions").status_code == 401
        assert c.get("/healthz").json() == {"status": "ok"}


def test_without_frontend_build_root_is_not_found(client: TestClient) -> None:
    assert client.get("/").status_code == 404


def test_missing_frontend_build_stops_startup(llm: ScriptedLlm, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        make_client(llm, frontend_dist=str(tmp_path / "nope"))
