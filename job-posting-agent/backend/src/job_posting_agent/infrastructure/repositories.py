"""SQL のリポジトリ。application/interfaces.py のインターフェースを実装する。

どのメソッドも持ち主（owner）で絞り込む。決まりごと（上限など）はサービスが決めて渡す。
"""

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..domain.models import (
    TEAM_OWNER,
    JobPosting,
    JobSummary,
    Perspective,
    SummaryListItem,
    UserId,
)
from .db.tables import JobPostingRow, JobSummaryRow, PerspectiveRow

Sessions = async_sessionmaker[AsyncSession]


class SqlJobPostingSource:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

    async def get(self, job_id: str) -> JobPosting | None:
        async with self._sessions() as s:
            row = await s.get(JobPostingRow, job_id)
            if row is None:
                return None
            return JobPosting(
                id=row.id, company=row.company, title=row.title, body=row.body, url=row.url
            )

    async def put(self, posting: JobPosting) -> None:
        """求人票を登録する。管理用のスクリプトとテストからだけ使う。"""
        async with self._sessions() as s:
            await s.merge(
                JobPostingRow(
                    id=posting.id,
                    company=posting.company,
                    title=posting.title,
                    body=posting.body,
                    url=posting.url,
                )
            )
            await s.commit()


class SqlSummaryRepository:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

    async def add(self, owner: UserId, summary: JobSummary) -> str:
        summary_id = str(uuid.uuid4())
        async with self._sessions() as s:
            s.add(
                JobSummaryRow(
                    id=summary_id,
                    owner_id=owner,
                    source_type=summary.source_type,
                    source_ref=summary.source_ref,
                    data=summary.model_dump(),
                )
            )
            await s.commit()
        return summary_id

    async def list(self, owner: UserId, limit: int) -> list[SummaryListItem]:
        async with self._sessions() as s:
            rows = await s.scalars(
                select(JobSummaryRow)
                .where(JobSummaryRow.owner_id == owner)
                .order_by(JobSummaryRow.created_at.desc())
                .limit(limit)
            )
            return [
                SummaryListItem(
                    id=r.id,
                    company=r.data.get("company"),
                    title=r.data.get("title"),
                    source_type=r.source_type,
                    created_at=r.created_at,
                )
                for r in rows
            ]

    async def get(self, owner: UserId, summary_id: str) -> JobSummary | None:
        async with self._sessions() as s:
            row = await s.scalar(
                select(JobSummaryRow).where(
                    JobSummaryRow.id == summary_id, JobSummaryRow.owner_id == owner
                )
            )
            return None if row is None else JobSummary.model_validate(row.data)


def _perspective(row: PerspectiveRow) -> Perspective:
    return Perspective(
        name=row.name,
        content=row.content,
        is_default=row.is_default,
        is_team_template=row.owner_id == TEAM_OWNER,
    )


class SqlPerspectiveRepository:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

    async def list_for(self, owner: str) -> list[Perspective]:
        async with self._sessions() as s:
            rows = await s.scalars(
                select(PerspectiveRow)
                .where(PerspectiveRow.owner_id == owner)
                .order_by(PerspectiveRow.name)
            )
            return [_perspective(r) for r in rows]

    async def find(self, owner: str, name: str) -> Perspective | None:
        async with self._sessions() as s:
            row = await s.scalar(
                select(PerspectiveRow).where(
                    PerspectiveRow.owner_id == owner, PerspectiveRow.name == name
                )
            )
            return None if row is None else _perspective(row)

    async def find_default(self, owner: str) -> Perspective | None:
        async with self._sessions() as s:
            row = await s.scalar(
                select(PerspectiveRow).where(
                    PerspectiveRow.owner_id == owner, PerspectiveRow.is_default.is_(True)
                )
            )
            return None if row is None else _perspective(row)

    async def upsert(
        self, owner: str, name: str, content: str, *, make_default: bool, max_per_owner: int
    ) -> Perspective | None:
        # 件数の確認、保存、デフォルトの切り替えを1つのトランザクションで行う
        async with self._sessions() as s:
            row = await s.scalar(
                select(PerspectiveRow).where(
                    PerspectiveRow.owner_id == owner, PerspectiveRow.name == name
                )
            )
            if row is None:
                count = await s.scalar(select(func.count()).where(PerspectiveRow.owner_id == owner))
                if (count or 0) >= max_per_owner:
                    return None
                row = PerspectiveRow(owner_id=owner, name=name, content=content, is_default=False)
                s.add(row)
            else:
                row.content = content
            if make_default:
                await s.execute(
                    update(PerspectiveRow)
                    .where(PerspectiveRow.owner_id == owner)
                    .values(is_default=False)
                )
                row.is_default = True
            await s.commit()
            return _perspective(row)

    async def delete(self, owner: str, name: str) -> bool:
        async with self._sessions() as s:
            result = await s.execute(
                delete(PerspectiveRow).where(
                    PerspectiveRow.owner_id == owner, PerspectiveRow.name == name
                )
            )
            await s.commit()
            return (result.rowcount or 0) > 0  # type: ignore[attr-defined]
