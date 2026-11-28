"""API サーバー。Cloud Run で動かし、前段に IAP を置く。

本番では、フロントエンドのビルド結果（FRONTEND_DIST）も同じサーバーから配信する。
同じドメインになるので、IAP のログインがそのまま効き、CORS の設定も要らない。
開発中は Vite の開発サーバーが /api をこのサーバーに中継する。

起動: uv run uvicorn --factory job_posting_agent.server:create_app --reload
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents import LlmAgent, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from . import db
from .agent import APP_NAME, build_agent
from .auth import Authenticator, AuthError
from .config import Settings, get_settings
from .rate_limit import RateLimiter

logger = logging.getLogger(__name__)

CSRF_HEADER = "x-requested-with"
PDF_MIME = "application/pdf"
TITLE_KEY = "title"
ATTACHMENT_PREFIX = "[添付ファイル: "


def create_app(
    settings: Settings | None = None,
    *,
    agent: LlmAgent | None = None,
    authenticator: Authenticator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    # 設定が足りなければ、起動の時点で止める（IAP_AUDIENCE がないまま公開しない）
    authenticator = authenticator or Authenticator(settings)
    limiter = RateLimiter(settings.rate_limit_per_minute)
    state: dict[str, Any] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        engine = await db.get_engine()
        session_service = DatabaseSessionService(db_engine=engine)
        state["sessions"] = session_service
        state["runner"] = Runner(
            app_name=APP_NAME, agent=agent or build_agent(), session_service=session_service
        )
        yield
        await state["runner"].close()

    app = FastAPI(title="求人票エージェント", lifespan=lifespan, docs_url=None, redoc_url=None)

    async def current_user(request: Request) -> str:
        try:
            return await authenticator.user_id(request.headers)
        except AuthError as e:
            raise HTTPException(status_code=401, detail="ログインが必要です") from e

    def require_csrf_header(request: Request) -> None:
        # 独自ヘッダーは、他のサイトのフォームやリンクからは付けられない
        if request.headers.get(CSRF_HEADER) != "fetch":
            raise HTTPException(status_code=403, detail="不正なリクエストです")

    User = Annotated[str, Depends(current_user)]

    async def owned_session(user: str, session_id: str) -> Any:
        # user_id 付きで探すので、他人のセッションIDを指定しても見つからない
        session = await state["sessions"].get_session(
            app_name=APP_NAME, user_id=user, session_id=session_id
        )
        if session is None:
            raise HTTPException(status_code=404, detail="会話が見つかりません")
        return session

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/me")
    async def me(user: User) -> dict[str, str]:
        return {"user": user}

    @app.get("/api/sessions")
    async def list_sessions(user: User) -> list[dict[str, Any]]:
        resp = await state["sessions"].list_sessions(app_name=APP_NAME, user_id=user)
        items = [
            {
                "id": s.id,
                "title": (s.state or {}).get(TITLE_KEY) or "新しい会話",
                "updated_at": s.last_update_time,
            }
            for s in resp.sessions
        ]
        return sorted(items, key=lambda x: x["updated_at"], reverse=True)

    @app.post("/api/sessions", dependencies=[Depends(require_csrf_header)])
    async def create_session(user: User) -> dict[str, str]:
        session = await state["sessions"].create_session(app_name=APP_NAME, user_id=user)
        return {"id": session.id}

    @app.get("/api/sessions/{session_id}")
    async def get_session(user: User, session_id: str) -> dict[str, Any]:
        session = await owned_session(user, session_id)
        return {"id": session.id, "messages": _messages(session.events)}

    @app.delete("/api/sessions/{session_id}", dependencies=[Depends(require_csrf_header)])
    async def delete_session(user: User, session_id: str) -> dict[str, str]:
        await owned_session(user, session_id)
        await state["sessions"].delete_session(
            app_name=APP_NAME, user_id=user, session_id=session_id
        )
        return {"status": "ok"}

    @app.post("/api/sessions/{session_id}/messages", dependencies=[Depends(require_csrf_header)])
    async def post_message(
        user: User,
        session_id: str,
        text: Annotated[str, Form()] = "",
        file: Annotated[UploadFile | None, File()] = None,
    ) -> StreamingResponse:
        session = await owned_session(user, session_id)
        text = text.strip()
        if len(text) > settings.max_message_chars:
            raise HTTPException(status_code=413, detail="メッセージが長すぎます")

        parts: list[types.Part] = []
        name = ""
        if text:
            parts.append(types.Part(text=text))
        if file is not None and file.filename:
            data = await file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="ファイルが大きすぎます")
            if not data.startswith(b"%PDF-"):
                raise HTTPException(status_code=415, detail="PDF だけを添付できます")
            name = file.filename[:200]
            parts.append(types.Part(text=f"{ATTACHMENT_PREFIX}{name}]"))
            parts.append(types.Part(inline_data=types.Blob(mime_type=PDF_MIME, data=data)))
        if not parts:
            raise HTTPException(status_code=400, detail="メッセージを入力してください")

        if not limiter.allow(user):
            raise HTTPException(status_code=429, detail="少し時間をおいてから送ってください")

        state_delta = None
        if not (session.state or {}).get(TITLE_KEY):
            state_delta = {TITLE_KEY: (text or name)[:40]}

        message = types.Content(role="user", parts=parts)
        return StreamingResponse(
            _stream(state["runner"], user, session_id, message, state_delta),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    # API より後に登録するので、/api や /healthz が優先される
    if settings.frontend_dist:
        dist = Path(settings.frontend_dist)
        if not (dist / "index.html").is_file():
            raise RuntimeError(f"FRONTEND_DIST に index.html がありません: {dist}")
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _texts(content: types.Content | None) -> str:
    if content is None or not content.parts:
        return ""
    return "".join(p.text or "" for p in content.parts if p.text and not p.thought)


async def _stream(
    runner: Runner,
    user: str,
    session_id: str,
    message: types.Content,
    state_delta: dict[str, Any] | None,
) -> AsyncIterator[str]:
    """ADK のイベントを、画面向けの SSE に変える。

    部分的なテキストは delta として送り、まとめて届いたテキストは、部分を送っていない
    ときだけ送る（同じ文章を2回表示しないため）。
    """
    streamed = ""
    try:
        async for event in runner.run_async(
            user_id=user,
            session_id=session_id,
            new_message=message,
            state_delta=state_delta,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            calls = event.get_function_calls()
            if event.partial:
                if not calls:
                    chunk = _texts(event.content)
                    if chunk:
                        streamed += chunk
                        yield _sse({"type": "delta", "text": chunk})
                continue
            for call in calls:
                yield _sse({"type": "tool", "name": call.name})
            final = _texts(event.content)
            if final and not streamed:
                yield _sse({"type": "delta", "text": final})
            streamed = ""
    except Exception:
        logger.exception("エージェントの実行に失敗しました session=%s", session_id)
        yield _sse({"type": "error", "message": "エラーが起きました。もう一度試してください"})
    yield _sse({"type": "done"})


def _messages(events: list[Any]) -> list[dict[str, Any]]:
    """保存された会話から、画面に出すメッセージだけを取り出す。"""
    out: list[dict[str, Any]] = []
    for event in events:
        if event.partial or event.content is None or not event.content.parts:
            continue
        if event.get_function_calls() or event.get_function_responses():
            continue
        role = "user" if event.author == "user" else "agent"
        attachments = [
            p.text.removeprefix(ATTACHMENT_PREFIX).removesuffix("]")
            for p in event.content.parts
            if role == "user" and p.text and p.text.startswith(ATTACHMENT_PREFIX)
        ]
        text = "".join(
            p.text
            for p in event.content.parts
            if p.text and not p.thought and not p.text.startswith(ATTACHMENT_PREFIX)
        )
        if text or attachments:
            out.append({"role": role, "text": text, "attachments": attachments})
    return out
