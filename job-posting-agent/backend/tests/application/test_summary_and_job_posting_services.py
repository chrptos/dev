import pytest

from job_posting_agent.application.job_posting_service import JobPostingService
from job_posting_agent.application.summary_service import SummaryService
from job_posting_agent.domain.errors import FetchFailed, NotFound
from job_posting_agent.domain.models import JobPosting, JobSummary, WebPage

from ..fakes import FakeJobPostingSource, FakeSummaryRepository, FakeWebPageFetcher

pytestmark = pytest.mark.anyio

ALICE = "alice@example.com"
BOB = "bob@example.com"


def summary(**kw: object) -> JobSummary:
    return JobSummary.model_validate({"source_type": "text", "source_ref": "pasted", **kw})


async def test_summaries_are_visible_only_to_owner() -> None:
    service = SummaryService(FakeSummaryRepository())
    sid = await service.save(ALICE, summary(company="株式会社A"))

    assert [s.id for s in await service.list(ALICE)] == [sid]
    assert await service.list(BOB) == []
    with pytest.raises(NotFound):
        await service.get(BOB, sid)
    assert (await service.get(ALICE, sid)).company == "株式会社A"


async def test_long_source_ref_is_truncated() -> None:
    repo = FakeSummaryRepository()
    sid = await SummaryService(repo).save(ALICE, summary(source_ref="x" * 5000))
    assert len(repo.rows[sid][1].source_ref) == 2000


async def test_job_posting_from_db_and_url() -> None:
    posting = JobPosting("J-001", "C社", "SRE", "本文", None)
    page = WebPage("https://jobs.example.com/1", "求人", "本文", False)
    fetcher = FakeWebPageFetcher({page.url: page})
    service = JobPostingService(FakeJobPostingSource([posting]), fetcher)

    assert await service.from_db(" J-001 ") == posting
    with pytest.raises(NotFound):
        await service.from_db("nope")
    assert await service.from_url(f"  {page.url} ") == page
    with pytest.raises(FetchFailed):
        await service.from_url("https://other.example.com/")
    assert fetcher.requested == [page.url, "https://other.example.com/"]
