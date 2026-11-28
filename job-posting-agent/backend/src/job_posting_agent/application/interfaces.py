"""サービスが使う外の機能の約束（インターフェース）。実装は infrastructure 層に置く。

Protocol なので、実装側はこのモジュールを import しなくてもよい（形が合えばよい）。
"""

from collections.abc import AsyncIterator, Mapping
from typing import Protocol

from ..domain.models import (
    AgentEvent,
    Conversation,
    ConversationSummary,
    JobPosting,
    JobSummary,
    Perspective,
    SummaryListItem,
    UserId,
    UserMessage,
    WebPage,
)


class Authenticator(Protocol):
    async def user_id(self, headers: Mapping[str, str]) -> UserId:
        """リクエストのヘッダーから利用者を決める。決められなければ Unauthenticated を投げる。"""
        ...


class JobPostingSource(Protocol):
    async def get(self, job_id: str) -> JobPosting | None: ...


class WebPageFetcher(Protocol):
    async def fetch(self, url: str) -> WebPage:
        """取得できなければ FetchFailed を投げる。"""
        ...


class SummaryRepository(Protocol):
    async def add(self, owner: UserId, summary: JobSummary) -> str: ...

    async def list(self, owner: UserId, limit: int) -> list[SummaryListItem]: ...

    async def get(self, owner: UserId, summary_id: str) -> JobSummary | None: ...


class PerspectiveRepository(Protocol):
    async def list_for(self, owner: str) -> list[Perspective]:
        """持ち主の観点を名前順に返す。"""
        ...

    async def find(self, owner: str, name: str) -> Perspective | None: ...

    async def find_default(self, owner: str) -> Perspective | None: ...

    async def upsert(
        self, owner: str, name: str, content: str, *, make_default: bool, max_per_owner: int
    ) -> Perspective | None:
        """作成か上書きをする。新しく作ると max_per_owner を超えるときは何もせず None を返す。"""
        ...

    async def delete(self, owner: str, name: str) -> bool: ...


class ConversationStore(Protocol):
    async def create(self, user: UserId) -> str: ...

    async def list(self, user: UserId) -> list[ConversationSummary]: ...

    async def get(self, user: UserId, conversation_id: str) -> Conversation | None:
        """利用者の会話だけを返す。他人の会話なら None。"""
        ...

    async def delete(self, user: UserId, conversation_id: str) -> None: ...


class AgentRunner(Protocol):
    def run(
        self, user: UserId, conversation_id: str, message: UserMessage, new_title: str | None
    ) -> AsyncIterator[AgentEvent]:
        """エージェントにメッセージを渡し、返答を少しずつ返す。

        失敗しても例外は投げず、AgentFailed を返して終わる。new_title があれば会話の題名にする。
        """
        ...


class RateLimiter(Protocol):
    def allow(self, key: str) -> bool: ...
