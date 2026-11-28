"""SQL のリポジトリ。持ち主での絞り込みと、1つのトランザクションでの上限の確認を確かめる。"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_posting_agent.domain.models import TEAM_OWNER, JobPosting, JobSummary, UserId
from job_posting_agent.infrastructure.repositories import (
    SqlJobPostingSource,
    SqlPerspectiveRepository,
    SqlSummaryRepository,
)

pytestmark = pytest.mark.anyio

Sessions = async_sessionmaker[AsyncSession]
ALICE = UserId("alice@example.com")
BOB = UserId("bob@example.com")


async def test_perspective_upsert_default_and_limit(sessions: Sessions) -> None:
    repo = SqlPerspectiveRepository(sessions)
    a = await repo.upsert(ALICE, "A", "a", make_default=True, max_per_owner=2)
    b = await repo.upsert(ALICE, "B", "b", make_default=True, max_per_owner=2)
    assert a is not None and b is not None
    assert (await repo.find_default(ALICE)) == b
    assert (await repo.find(ALICE, "A")).is_default is False  # type: ignore[union-attr]

    # 新しく作ると上限を超えるときは保存しない。上書きはできる
    assert await repo.upsert(ALICE, "C", "c", make_default=False, max_per_owner=2) is None
    updated = await repo.upsert(ALICE, "A", "a2", make_default=False, max_per_owner=2)
    assert updated is not None and updated.content == "a2"

    await repo.upsert(TEAM_OWNER, "T", "t", make_default=False, max_per_owner=10)
    assert [p.name for p in await repo.list_for(ALICE)] == ["A", "B"]
    assert [p.is_team_template for p in await repo.list_for(TEAM_OWNER)] == [True]
    assert await repo.list_for(BOB) == []
    assert await repo.delete(BOB, "A") is False
    assert await repo.delete(ALICE, "A") is True


async def test_summaries_are_filtered_by_owner(sessions: Sessions) -> None:
    repo = SqlSummaryRepository(sessions)
    sid = await repo.add(ALICE, JobSummary(company="A社", source_type="url", source_ref="u"))
    assert [i.company for i in await repo.list(ALICE, 20)] == ["A社"]
    assert await repo.list(BOB, 20) == []
    assert await repo.get(BOB, sid) is None
    found = await repo.get(ALICE, sid)
    assert found is not None and found.company == "A社"


async def test_job_posting_source(sessions: Sessions) -> None:
    source = SqlJobPostingSource(sessions)
    posting = JobPosting("J-001", "C社", "SRE", "本文です", None)
    await source.put(posting)
    assert await source.get("J-001") == posting
    assert await source.get("nope") is None
