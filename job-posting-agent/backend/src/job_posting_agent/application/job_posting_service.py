"""求人票を入手するサービス（DB と URL）。PDF と貼り付けたテキストは AI が直接読む。"""

from ..domain.errors import NotFound
from ..domain.models import JobPosting, WebPage
from .interfaces import JobPostingSource, WebPageFetcher


class JobPostingService:
    def __init__(self, source: JobPostingSource, fetcher: WebPageFetcher) -> None:
        self._source = source
        self._fetcher = fetcher

    async def from_db(self, job_id: str) -> JobPosting:
        posting = await self._source.get(job_id.strip())
        if posting is None:
            raise NotFound(f"求人ID {job_id.strip()} の求人票は見つかりませんでした")
        return posting

    async def from_url(self, url: str) -> WebPage:
        return await self._fetcher.fetch(url.strip())
