"""ドメインの型と決まりごと。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, NewType

from pydantic import BaseModel, Field

from .errors import InvalidInput, Unauthenticated

# --- 利用者 ---

UserId = NewType("UserId", str)

# チーム共通の観点テンプレートの持ち主。IAP のメールアドレスとは重ならない
TEAM_OWNER = "__team__"


def ensure_user(user: str) -> UserId:
    """利用者として扱ってよい値か確かめる。サービスの入口で必ず呼ぶ。"""
    if not user or user == TEAM_OWNER:
        raise Unauthenticated("利用者を特定できません")
    return UserId(user)


# --- 求人票 ---

SourceType = Literal["db", "pdf", "url", "text"]


@dataclass(frozen=True)
class JobPosting:
    """求人票の元データ（DB に入っているもの）。"""

    id: str
    company: str | None
    title: str | None
    body: str
    url: str | None


@dataclass(frozen=True)
class WebPage:
    """URL から取得した求人ページの本文。"""

    url: str
    title: str | None
    text: str
    truncated: bool


class JobSummary(BaseModel):
    """求人票のまとめ。求人票に書かれていない項目は null か空のリストにし、推測で埋めない。"""

    company: str | None = Field(None, description="会社名")
    title: str | None = Field(None, description="職種・ポジション名")
    employment_type: str | None = Field(
        None, description="雇用形態（正社員、契約社員、業務委託など）"
    )
    location: str | None = Field(None, description="勤務地")
    remote_policy: str | None = Field(None, description="リモート可否や出社頻度")
    salary: str | None = Field(None, description="給与（求人票の表記のまま）")
    required_skills: list[str] = Field(default_factory=list, description="必須スキル・経験")
    preferred_skills: list[str] = Field(default_factory=list, description="歓迎スキル・経験")
    hiring_background: str | None = Field(None, description="募集背景")
    deadline: str | None = Field(None, description="応募締切")
    other_notes: str | None = Field(None, description="上の項目に入らない重要な情報")
    source_type: SourceType = Field(description="求人票の入手元: db / pdf / url / text")
    source_ref: str = Field(description="出典: 求人ID、PDF のファイル名、URL、または 'pasted'")


@dataclass(frozen=True)
class SummaryListItem:
    id: str
    company: str | None
    title: str | None
    source_type: str
    created_at: datetime


# --- 観点 ---

MAX_PERSPECTIVE_NAME = 50
MAX_PERSPECTIVE_CONTENT = 2000
MAX_PERSPECTIVES_PER_USER = 30


@dataclass(frozen=True)
class Perspective:
    name: str
    content: str
    is_default: bool
    is_team_template: bool


def normalize_perspective(name: str, content: str) -> tuple[str, str]:
    """観点の名前と内容を整え、長さの決まりを確かめる。"""
    name = name.strip()
    content = content.strip()
    if not name or len(name) > MAX_PERSPECTIVE_NAME:
        raise InvalidInput(f"観点の名前は1〜{MAX_PERSPECTIVE_NAME}文字にしてください")
    if not content or len(content) > MAX_PERSPECTIVE_CONTENT:
        raise InvalidInput(f"観点の内容は1〜{MAX_PERSPECTIVE_CONTENT}文字にしてください")
    return name, content


# --- 会話 ---

PDF_MIME = "application/pdf"
MAX_TITLE_CHARS = 40
MAX_FILENAME_CHARS = 200


@dataclass(frozen=True)
class Attachment:
    filename: str
    mime_type: str
    data: bytes


@dataclass(frozen=True)
class UserMessage:
    text: str
    attachment: Attachment | None = None


@dataclass(frozen=True)
class ConversationSummary:
    id: str
    title: str | None
    updated_at: float


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "agent"]
    text: str
    attachments: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Conversation:
    id: str
    title: str | None
    messages: list[ChatMessage]


# --- エージェントの返答 ---


@dataclass(frozen=True)
class TextDelta:
    """返答の文章の一部。"""

    text: str


@dataclass(frozen=True)
class ToolCalled:
    """エージェントがツールを呼んだ。"""

    name: str


@dataclass(frozen=True)
class AgentFailed:
    """エージェントの実行に失敗した。message は利用者に見せてよい文。"""

    message: str


AgentEvent = TextDelta | ToolCalled | AgentFailed
