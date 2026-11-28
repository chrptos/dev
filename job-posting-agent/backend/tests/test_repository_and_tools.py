"""観点とまとめが、利用者ごとに分かれていることを確かめる。"""

from types import SimpleNamespace

import pytest

from job_posting_agent import db, repository, tools
from job_posting_agent.db import TEAM_OWNER, JobPosting
from job_posting_agent.repository import RepositoryError
from job_posting_agent.schemas import JobSummary

pytestmark = pytest.mark.anyio

ALICE = "alice@example.com"
BOB = "bob@example.com"


def ctx(user: str) -> SimpleNamespace:
    return SimpleNamespace(user_id=user)


def summary(**kw: object) -> JobSummary:
    return JobSummary(source_type="text", source_ref="pasted", **kw)  # type: ignore[arg-type]


async def test_perspectives_are_separated_by_user() -> None:
    await repository.save_perspective(ALICE, "年収重視", "年収とリモート可否を見る")
    await repository.save_perspective(BOB, "スキル重視", "必須スキルの差を見る")

    alice = await repository.list_perspectives(ALICE)
    assert [p["name"] for p in alice] == ["年収重視"]
    assert await repository.get_perspective(ALICE, "スキル重視") is None
    # 他人の観点は削除できない
    assert await repository.delete_perspective(ALICE, "スキル重視") is False
    assert await repository.get_perspective(BOB, "スキル重視") is not None


async def test_team_template_is_shared_but_read_only() -> None:
    await repository.save_team_template("標準", "チーム標準の観点")

    for user in (ALICE, BOB):
        names = [p["name"] for p in await repository.list_perspectives(user)]
        assert names == ["標準"]
        found = await repository.get_perspective(user, "標準")
        assert found is not None
        assert found["is_team_template"] is True

    # 同じ名前で保存すると本人の観点になり、テンプレートは変わらない
    await repository.save_perspective(ALICE, "標準", "自分用に変えた")
    alice_view = await repository.get_perspective(ALICE, "標準")
    bob_view = await repository.get_perspective(BOB, "標準")
    assert alice_view is not None and alice_view["content"] == "自分用に変えた"
    assert bob_view is not None and bob_view["content"] == "チーム標準の観点"
    assert await repository.delete_perspective(ALICE, "標準") is True
    after = await repository.get_perspective(ALICE, "標準")
    assert after is not None and after["is_team_template"] is True


async def test_team_owner_cannot_be_used_as_user() -> None:
    with pytest.raises(RepositoryError):
        await repository.save_perspective(TEAM_OWNER, "x", "y")
    with pytest.raises(RepositoryError):
        await repository.list_perspectives("")


async def test_default_perspective_switches() -> None:
    await repository.save_perspective(ALICE, "A", "a", make_default=True)
    await repository.save_perspective(ALICE, "B", "b", make_default=True)
    default = await repository.get_perspective(ALICE)
    assert default is not None and default["name"] == "B"
    assert await repository.get_perspective(BOB) is None


@pytest.mark.parametrize(
    ("name", "content"), [("", "a"), ("x" * 51, "a"), ("ok", ""), ("ok", "x" * 2001)]
)
async def test_perspective_length_limits(name: str, content: str) -> None:
    with pytest.raises(RepositoryError):
        await repository.save_perspective(ALICE, name, content)


async def test_summaries_are_visible_only_to_owner() -> None:
    sid = await repository.save_summary(ALICE, summary(company="株式会社A"))
    assert [s["id"] for s in await repository.list_summaries(ALICE)] == [sid]
    assert await repository.list_summaries(BOB) == []
    assert await repository.get_summary(BOB, sid) is None
    found = await repository.get_summary(ALICE, sid)
    assert found is not None and found["company"] == "株式会社A"


async def test_tools_use_tool_context_user() -> None:
    result = await tools.save_perspective("観点", "内容", True, ctx(ALICE))  # type: ignore[arg-type]
    assert result["status"] == "ok"
    assert (await tools.get_perspective("", ctx(ALICE)))["status"] == "ok"  # type: ignore[arg-type]
    assert (await tools.get_perspective("", ctx(BOB)))["status"] == "error"  # type: ignore[arg-type]

    saved = await tools.save_job_summary(
        {"company": "B社", "source_type": "url", "source_ref": "https://example.com"},  # type: ignore[arg-type]
        ctx(BOB),  # type: ignore[arg-type]
    )
    assert saved["status"] == "ok"
    got_alice = await tools.get_job_summary(saved["summary_id"], ctx(ALICE))  # type: ignore[arg-type]
    assert got_alice["status"] == "error"


async def test_fetch_from_db_marks_body_untrusted() -> None:
    async with db.session() as s:
        s.add(JobPosting(id="J-001", company="C社", title="SRE", body="本文です"))
        await s.commit()
    result = await tools.fetch_job_posting_from_db(" J-001 ")
    assert result["status"] == "ok"
    assert result["untrusted_content"] == "本文です"
    assert "body" not in result["posting"]
    assert (await tools.fetch_job_posting_from_db("nope"))["status"] == "error"
