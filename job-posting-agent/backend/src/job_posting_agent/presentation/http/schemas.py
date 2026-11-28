"""HTTP のレスポンスの形。フロントエンドの src/types.ts と合わせる。"""

from typing import Literal

from pydantic import BaseModel

from ...domain.models import Conversation, ConversationSummary

UNTITLED = "新しい会話"


class MeResponse(BaseModel):
    user: str


class CreatedResponse(BaseModel):
    id: str


class StatusResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ConversationItem(BaseModel):
    id: str
    title: str
    updated_at: float

    @classmethod
    def of(cls, c: ConversationSummary) -> "ConversationItem":
        return cls(id=c.id, title=c.title or UNTITLED, updated_at=c.updated_at)


class MessageOut(BaseModel):
    role: Literal["user", "agent"]
    text: str
    attachments: list[str]


class ConversationOut(BaseModel):
    id: str
    messages: list[MessageOut]

    @classmethod
    def of(cls, c: Conversation) -> "ConversationOut":
        return cls(
            id=c.id,
            messages=[
                MessageOut(role=m.role, text=m.text, attachments=list(m.attachments))
                for m in c.messages
            ],
        )
