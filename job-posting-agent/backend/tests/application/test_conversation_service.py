"""会話のサービス。持ち主の確認、入力の決まり、回数制限、題名の付け方を確かめる。"""

import pytest

from job_posting_agent.application.conversation_service import ConversationService, MessageLimits
from job_posting_agent.domain.errors import (
    InvalidInput,
    NotFound,
    PayloadTooLarge,
    RateLimited,
    UnsupportedAttachment,
)
from job_posting_agent.domain.models import PDF_MIME, Attachment, TextDelta

from ..fakes import CountingLimiter, FakeAgentRunner, FakeConversationStore

pytestmark = pytest.mark.anyio

ALICE = "alice@example.com"
BOB = "bob@example.com"
PDF = Attachment("job.pdf", "application/octet-stream", b"%PDF-1.7 dummy")


class Env:
    def __init__(self, limit: int = 1000) -> None:
        self.store = FakeConversationStore()
        self.runner = FakeAgentRunner()
        self.limiter = CountingLimiter(limit)
        self.service = ConversationService(
            self.store,
            self.runner,
            self.limiter,
            MessageLimits(max_message_chars=100, max_upload_bytes=50),
        )


async def collect(service: ConversationService, *args: object) -> list[object]:
    return [e async for e in await service.send_message(*args)]  # type: ignore[arg-type]


async def test_send_message_runs_agent_and_sets_title_once() -> None:
    env = Env()
    cid = await env.service.start(ALICE)

    assert await collect(env.service, ALICE, cid, "  求人をまとめて  ", None) == [TextDelta("ok")]
    call = env.runner.calls[0]
    assert (call.user, call.conversation_id, call.message.text) == (ALICE, cid, "求人をまとめて")
    assert call.new_title == "求人をまとめて"

    env.store.rows[cid].title = "求人をまとめて"
    await collect(env.service, ALICE, cid, "続き", None)
    assert env.runner.calls[1].new_title is None


async def test_title_falls_back_to_attachment_name() -> None:
    env = Env()
    cid = await env.service.start(ALICE)
    await collect(env.service, ALICE, cid, "", PDF)
    call = env.runner.calls[0]
    assert call.new_title == "job.pdf"
    # 添付ファイルの形式はサービスが PDF に決める
    assert call.message.attachment is not None
    assert call.message.attachment.mime_type == PDF_MIME


async def test_other_users_conversation_is_not_found() -> None:
    env = Env()
    cid = await env.service.start(ALICE)
    with pytest.raises(NotFound):
        await env.service.get(BOB, cid)
    with pytest.raises(NotFound):
        await env.service.send_message(BOB, cid, "hi", None)
    with pytest.raises(NotFound):
        await env.service.delete(BOB, cid)
    assert await env.service.list(BOB) == []
    assert env.runner.calls == []
    assert cid in env.store.rows


@pytest.mark.parametrize(
    ("text", "attachment", "error"),
    [
        ("x" * 101, None, PayloadTooLarge),
        ("", Attachment("a.pdf", PDF_MIME, b"%PDF-" + b"x" * 50), PayloadTooLarge),
        ("x", Attachment("a.pdf", PDF_MIME, b"<html>not pdf"), UnsupportedAttachment),
        ("   ", None, InvalidInput),
    ],
)
async def test_invalid_messages_do_not_reach_the_agent(
    text: str, attachment: Attachment | None, error: type[Exception]
) -> None:
    env = Env()
    cid = await env.service.start(ALICE)
    with pytest.raises(error):
        await env.service.send_message(ALICE, cid, text, attachment)
    assert env.runner.calls == []
    # 入力の誤りは回数に数えない
    assert env.limiter.hits == {}


async def test_rate_limit_is_per_user() -> None:
    env = Env(limit=2)
    alice = await env.service.start(ALICE)
    bob = await env.service.start(BOB)
    await env.service.send_message(ALICE, alice, "1", None)
    await env.service.send_message(ALICE, alice, "2", None)
    with pytest.raises(RateLimited):
        await env.service.send_message(ALICE, alice, "3", None)
    await env.service.send_message(BOB, bob, "1", None)


async def test_list_is_newest_first_and_delete_removes() -> None:
    env = Env()
    first = await env.service.start(ALICE)
    second = await env.service.start(ALICE)
    assert [c.id for c in await env.service.list(ALICE)] == [second, first]
    await env.service.delete(ALICE, first)
    assert [c.id for c in await env.service.list(ALICE)] == [second]
