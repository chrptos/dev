"""application/interfaces.py の偽物。サービスの単体テストで、DB や ADK の代わりに使う。"""

import itertools
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass, field, replace

from job_posting_agent.domain.errors import FetchFailed
from job_posting_agent.domain.models import (
    TEAM_OWNER,
    AgentEvent,
    Conversation,
    ConversationSummary,
    JobPosting,
    JobSummary,
    Perspective,
    SummaryListItem,
    TextDelta,
    UserId,
    UserMessage,
    WebPage,
)


class FakePerspectiveRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Perspective] = {}

    async def list_for(self, owner: str) -> list[Perspective]:
        return [p for (o, _), p in sorted(self.rows.items()) if o == owner]

    async def find(self, owner: str, name: str) -> Perspective | None:
        return self.rows.get((owner, name))

    async def find_default(self, owner: str) -> Perspective | None:
        return next((p for (o, _), p in self.rows.items() if o == owner and p.is_default), None)

    async def upsert(
        self, owner: str, name: str, content: str, *, make_default: bool, max_per_owner: int
    ) -> Perspective | None:
        key = (owner, name)
        if key not in self.rows and sum(o == owner for o, _ in self.rows) >= max_per_owner:
            return None
        current = self.rows.get(key)
        is_default = current.is_default if current else False
        if make_default:
            for k, p in list(self.rows.items()):
                if k[0] == owner:
                    self.rows[k] = replace(p, is_default=False)
            is_default = True
        self.rows[key] = Perspective(name, content, is_default, owner == TEAM_OWNER)
        return self.rows[key]

    async def delete(self, owner: str, name: str) -> bool:
        return self.rows.pop((owner, name), None) is not None


class FakeSummaryRepository:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[UserId, JobSummary]] = {}
        self._ids = itertools.count(1)

    async def add(self, owner: UserId, summary: JobSummary) -> str:
        summary_id = f"s{next(self._ids)}"
        self.rows[summary_id] = (owner, summary)
        return summary_id

    async def list(self, owner: UserId, limit: int) -> list[SummaryListItem]:
        from datetime import UTC, datetime

        return [
            SummaryListItem(sid, s.company, s.title, s.source_type, datetime.now(UTC))
            for sid, (o, s) in self.rows.items()
            if o == owner
        ][:limit]

    async def get(self, owner: UserId, summary_id: str) -> JobSummary | None:
        found = self.rows.get(summary_id)
        return found[1] if found and found[0] == owner else None


@dataclass
class StoredConversation:
    user: UserId
    title: str | None = None
    updated_at: float = 0.0


class FakeConversationStore:
    def __init__(self) -> None:
        self.rows: dict[str, StoredConversation] = {}
        self._ids = itertools.count(1)

    async def create(self, user: UserId) -> str:
        cid = f"c{next(self._ids)}"
        self.rows[cid] = StoredConversation(user, updated_at=float(len(self.rows)))
        return cid

    async def list(self, user: UserId) -> list[ConversationSummary]:
        return [
            ConversationSummary(cid, c.title, c.updated_at)
            for cid, c in self.rows.items()
            if c.user == user
        ]

    async def get(self, user: UserId, conversation_id: str) -> Conversation | None:
        c = self.rows.get(conversation_id)
        if c is None or c.user != user:
            return None
        return Conversation(conversation_id, c.title, [])

    async def delete(self, user: UserId, conversation_id: str) -> None:
        self.rows.pop(conversation_id, None)


@dataclass
class RunCall:
    user: UserId
    conversation_id: str
    message: UserMessage
    new_title: str | None


@dataclass
class FakeAgentRunner:
    events: list[AgentEvent] = field(default_factory=lambda: [TextDelta("ok")])
    calls: list[RunCall] = field(default_factory=list)

    async def run(
        self, user: UserId, conversation_id: str, message: UserMessage, new_title: str | None
    ) -> AsyncIterator[AgentEvent]:
        self.calls.append(RunCall(user, conversation_id, message, new_title))
        for e in self.events:
            yield e


class CountingLimiter:
    def __init__(self, limit: int = 1000) -> None:
        self.limit = limit
        self.hits: dict[str, int] = {}

    def allow(self, key: str) -> bool:
        self.hits[key] = self.hits.get(key, 0) + 1
        return self.hits[key] <= self.limit


class FakeJobPostingSource:
    def __init__(self, postings: Iterable[JobPosting] = ()) -> None:
        self.rows = {p.id: p for p in postings}

    async def get(self, job_id: str) -> JobPosting | None:
        return self.rows.get(job_id)


class FakeWebPageFetcher:
    def __init__(self, pages: dict[str, WebPage] | None = None) -> None:
        self.pages = pages or {}
        self.requested: list[str] = []

    async def fetch(self, url: str) -> WebPage:
        self.requested.append(url)
        if url not in self.pages:
            raise FetchFailed("ページを取得できませんでした")
        return self.pages[url]
