"""求人のまとめのサービス。まとめた本人だけが読める。"""

from ..domain.errors import NotFound
from ..domain.models import JobSummary, SummaryListItem, ensure_user
from .interfaces import SummaryRepository

MAX_SOURCE_REF_CHARS = 2000


class SummaryService:
    def __init__(self, repository: SummaryRepository) -> None:
        self._repo = repository

    async def save(self, user: str, summary: JobSummary) -> str:
        summary = summary.model_copy(
            update={"source_ref": summary.source_ref[:MAX_SOURCE_REF_CHARS]}
        )
        return await self._repo.add(ensure_user(user), summary)

    async def list(self, user: str, limit: int = 20) -> list[SummaryListItem]:
        return await self._repo.list(ensure_user(user), limit)

    async def get(self, user: str, summary_id: str) -> JobSummary:
        found = await self._repo.get(ensure_user(user), summary_id)
        if found is None:
            raise NotFound("そのまとめは見つかりませんでした")
        return found
