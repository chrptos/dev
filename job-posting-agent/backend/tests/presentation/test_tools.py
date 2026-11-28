"""AI のツール。

利用者を tool_context.user_id から取り、エラーを AI 向けの形にすることを確かめる。
"""

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from job_posting_agent.application.job_posting_service import JobPostingService
from job_posting_agent.application.perspective_service import PerspectiveService
from job_posting_agent.application.services import AgentServices
from job_posting_agent.application.summary_service import SummaryService
from job_posting_agent.domain.models import JobPosting
from job_posting_agent.presentation.agent.tools import build_tools

from ..fakes import (
    FakeJobPostingSource,
    FakePerspectiveRepository,
    FakeSummaryRepository,
    FakeWebPageFetcher,
)

pytestmark = pytest.mark.anyio

ALICE = SimpleNamespace(user_id="alice@example.com")
BOB = SimpleNamespace(user_id="bob@example.com")


@pytest.fixture
def tools() -> dict[str, Callable[..., Any]]:
    services = AgentServices(
        job_postings=JobPostingService(
            FakeJobPostingSource([JobPosting("J-001", "C社", "SRE", "本文です", None)]),
            FakeWebPageFetcher(),
        ),
        summaries=SummaryService(FakeSummaryRepository()),
        perspectives=PerspectiveService(FakePerspectiveRepository()),
    )
    return {t.__name__: t for t in build_tools(services)}


async def test_tools_use_tool_context_user(tools: dict[str, Callable[..., Any]]) -> None:
    assert (await tools["save_perspective"]("観点", "内容", True, ALICE))["status"] == "ok"
    assert (await tools["get_perspective"]("", ALICE))["perspective"]["name"] == "観点"
    assert (await tools["get_perspective"]("", BOB))["status"] == "error"

    saved = await tools["save_job_summary"](
        {"company": "B社", "source_type": "url", "source_ref": "https://example.com"}, BOB
    )
    assert saved["status"] == "ok"
    assert (await tools["get_job_summary"](saved["summary_id"], ALICE))["status"] == "error"
    got = await tools["get_job_summary"](saved["summary_id"], BOB)
    assert got["summary"]["company"] == "B社"
    assert [s["company"] for s in (await tools["list_my_job_summaries"](BOB))["summaries"]] == [
        "B社"
    ]


async def test_external_content_is_marked_untrusted(tools: dict[str, Callable[..., Any]]) -> None:
    result = await tools["fetch_job_posting_from_db"](" J-001 ")
    assert result["status"] == "ok"
    assert result["untrusted_content"] == "本文です"
    assert "body" not in result["posting"]
    assert "指示" in result["note"]


async def test_errors_become_messages_for_the_ai(tools: dict[str, Callable[..., Any]]) -> None:
    assert (await tools["fetch_job_posting_from_db"]("nope")) == {
        "status": "error",
        "message": "求人ID nope の求人票は見つかりませんでした",
    }
    assert (await tools["fetch_job_posting_from_url"]("https://x.example/"))["status"] == "error"
    assert (await tools["save_perspective"]("", "x", False, ALICE))["status"] == "error"
    assert (await tools["delete_perspective"]("ない", ALICE))["status"] == "error"


def test_all_tools_are_exposed(tools: dict[str, Callable[..., Any]]) -> None:
    assert set(tools) == {
        "fetch_job_posting_from_db",
        "fetch_job_posting_from_url",
        "save_job_summary",
        "list_my_job_summaries",
        "get_job_summary",
        "list_perspectives",
        "get_perspective",
        "save_perspective",
        "delete_perspective",
    }
