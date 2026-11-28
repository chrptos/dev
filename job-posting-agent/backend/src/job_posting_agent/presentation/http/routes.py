"""API のルート。利用者を受け取ってサービスを呼び、結果をレスポンスの形にするだけ。"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from ...domain.models import PDF_MIME, Attachment
from .deps import Context, User, require_csrf_header
from .schemas import (
    ConversationItem,
    ConversationOut,
    CreatedResponse,
    MeResponse,
    StatusResponse,
)
from .sse import to_sse

router = APIRouter(prefix="/api")
csrf = [Depends(require_csrf_header)]


@router.get("/me")
async def me(user: User) -> MeResponse:
    return MeResponse(user=user)


@router.get("/sessions")
async def list_sessions(user: User, ctx: Context) -> list[ConversationItem]:
    items = await ctx.services.conversations.list(user)
    return [ConversationItem.of(c) for c in items]


@router.post("/sessions", dependencies=csrf)
async def create_session(user: User, ctx: Context) -> CreatedResponse:
    return CreatedResponse(id=await ctx.services.conversations.start(user))


@router.get("/sessions/{session_id}")
async def get_session(user: User, ctx: Context, session_id: str) -> ConversationOut:
    return ConversationOut.of(await ctx.services.conversations.get(user, session_id))


@router.delete("/sessions/{session_id}", dependencies=csrf)
async def delete_session(user: User, ctx: Context, session_id: str) -> StatusResponse:
    await ctx.services.conversations.delete(user, session_id)
    return StatusResponse()


@router.post("/sessions/{session_id}/messages", dependencies=csrf)
async def post_message(
    user: User,
    ctx: Context,
    session_id: str,
    text: Annotated[str, Form()] = "",
    file: Annotated[UploadFile | None, File()] = None,
) -> StreamingResponse:
    attachment = None
    if file is not None and file.filename:
        data = await file.read(ctx.upload_read_limit)
        attachment = Attachment(filename=file.filename, mime_type=PDF_MIME, data=data)
    events = await ctx.services.conversations.send_message(user, session_id, text, attachment)
    return StreamingResponse(
        to_sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
