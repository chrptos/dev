"""会話の保存先（ConversationStore の実装）。ADK のセッションをそのまま使う。"""

from typing import Any

from google.adk.sessions import BaseSessionService

from ...domain.models import ChatMessage, Conversation, ConversationSummary, UserId
from . import APP_NAME, ATTACHMENT_PREFIX, TITLE_KEY


class AdkConversationStore:
    def __init__(self, sessions: BaseSessionService) -> None:
        self._sessions = sessions

    async def create(self, user: UserId) -> str:
        session = await self._sessions.create_session(app_name=APP_NAME, user_id=user)
        return session.id

    async def list(self, user: UserId) -> list[ConversationSummary]:
        resp = await self._sessions.list_sessions(app_name=APP_NAME, user_id=user)
        return [
            ConversationSummary(
                id=s.id, title=(s.state or {}).get(TITLE_KEY), updated_at=s.last_update_time
            )
            for s in resp.sessions
        ]

    async def get(self, user: UserId, conversation_id: str) -> Conversation | None:
        # user_id 付きで探すので、他人のセッションIDを指定しても見つからない
        session = await self._sessions.get_session(
            app_name=APP_NAME, user_id=user, session_id=conversation_id
        )
        if session is None:
            return None
        return Conversation(
            id=session.id,
            title=(session.state or {}).get(TITLE_KEY),
            messages=_messages(session.events),
        )

    async def delete(self, user: UserId, conversation_id: str) -> None:
        await self._sessions.delete_session(
            app_name=APP_NAME, user_id=user, session_id=conversation_id
        )


def _messages(events: list[Any]) -> list[ChatMessage]:
    """保存されたイベントから、画面に出すメッセージだけを取り出す。"""
    out: list[ChatMessage] = []
    for event in events:
        if event.partial or event.content is None or not event.content.parts:
            continue
        if event.get_function_calls() or event.get_function_responses():
            continue
        is_user = event.author == "user"
        attachments = [
            p.text.removeprefix(ATTACHMENT_PREFIX).removesuffix("]")
            for p in event.content.parts
            if is_user and p.text and p.text.startswith(ATTACHMENT_PREFIX)
        ]
        text = "".join(
            p.text
            for p in event.content.parts
            if p.text and not p.thought and not p.text.startswith(ATTACHMENT_PREFIX)
        )
        if text or attachments:
            out.append(
                ChatMessage(role="user" if is_user else "agent", text=text, attachments=attachments)
            )
    return out
