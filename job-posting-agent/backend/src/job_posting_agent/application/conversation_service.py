"""会話のサービス。持ち主の確認、入力の決まり、回数制限はここで守る。"""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from ..domain.errors import (
    InvalidInput,
    NotFound,
    PayloadTooLarge,
    RateLimited,
    UnsupportedAttachment,
)
from ..domain.models import (
    MAX_FILENAME_CHARS,
    MAX_TITLE_CHARS,
    PDF_MIME,
    AgentEvent,
    Attachment,
    Conversation,
    ConversationSummary,
    UserMessage,
    ensure_user,
)
from .interfaces import AgentRunner, ConversationStore, RateLimiter


@dataclass(frozen=True)
class MessageLimits:
    max_message_chars: int
    max_upload_bytes: int


class ConversationService:
    def __init__(
        self,
        store: ConversationStore,
        runner: AgentRunner,
        limiter: RateLimiter,
        limits: MessageLimits,
    ) -> None:
        self._store = store
        self._runner = runner
        self._limiter = limiter
        self._limits = limits

    async def start(self, user: str) -> str:
        return await self._store.create(ensure_user(user))

    async def list(self, user: str) -> list[ConversationSummary]:
        items = await self._store.list(ensure_user(user))
        return sorted(items, key=lambda c: c.updated_at, reverse=True)

    async def get(self, user: str, conversation_id: str) -> Conversation:
        conversation = await self._store.get(ensure_user(user), conversation_id)
        if conversation is None:
            raise NotFound("会話が見つかりません")
        return conversation

    async def delete(self, user: str, conversation_id: str) -> None:
        await self.get(user, conversation_id)
        await self._store.delete(ensure_user(user), conversation_id)

    async def send_message(
        self, user: str, conversation_id: str, text: str, attachment: Attachment | None
    ) -> AsyncIterator[AgentEvent]:
        """入力を確かめてからエージェントに渡す。

        確かめるところまでは呼んだ時点で行い、問題があればここで例外を投げる。
        返答は戻り値の AsyncIterator から少しずつ受け取る。
        """
        uid = ensure_user(user)
        conversation = await self.get(uid, conversation_id)

        text = text.strip()
        if len(text) > self._limits.max_message_chars:
            raise PayloadTooLarge("メッセージが長すぎます")
        if attachment is not None:
            attachment = self._check_attachment(attachment)
        if not text and attachment is None:
            raise InvalidInput("メッセージを入力してください")
        if not self._limiter.allow(uid):
            raise RateLimited("少し時間をおいてから送ってください")

        new_title = None
        if not conversation.title:
            new_title = (text or (attachment.filename if attachment else ""))[:MAX_TITLE_CHARS]
        return self._runner.run(uid, conversation_id, UserMessage(text, attachment), new_title)

    def _check_attachment(self, attachment: Attachment) -> Attachment:
        if len(attachment.data) > self._limits.max_upload_bytes:
            raise PayloadTooLarge("ファイルが大きすぎます")
        if not attachment.data.startswith(b"%PDF-"):
            raise UnsupportedAttachment("PDF だけを添付できます")
        return Attachment(
            filename=attachment.filename[:MAX_FILENAME_CHARS] or "attachment.pdf",
            mime_type=PDF_MIME,
            data=attachment.data,
        )
