"""観点のサービス。偽のリポジトリで、利用者ごとの分離とテンプレートの扱いを確かめる。"""

import pytest

from job_posting_agent.application.perspective_service import PerspectiveService
from job_posting_agent.domain.errors import InvalidInput, NotFound, Unauthenticated
from job_posting_agent.domain.models import MAX_PERSPECTIVES_PER_USER, TEAM_OWNER

from ..fakes import FakePerspectiveRepository

pytestmark = pytest.mark.anyio

ALICE = "alice@example.com"
BOB = "bob@example.com"


@pytest.fixture
def service() -> PerspectiveService:
    return PerspectiveService(FakePerspectiveRepository())


async def test_perspectives_are_separated_by_user(service: PerspectiveService) -> None:
    await service.save(ALICE, "年収重視", "年収とリモート可否を見る", False)
    await service.save(BOB, "スキル重視", "必須スキルの差を見る", False)

    assert [p.name for p in await service.list(ALICE)] == ["年収重視"]
    with pytest.raises(NotFound):
        await service.get(ALICE, "スキル重視")
    with pytest.raises(NotFound):
        await service.delete(ALICE, "スキル重視")
    assert (await service.get(BOB, "スキル重視")).content == "必須スキルの差を見る"


async def test_team_template_is_shared_and_own_one_wins(service: PerspectiveService) -> None:
    await service.save_team_template("標準", "チーム標準の観点")
    await service.save(ALICE, "自分用", "自分の観点", False)

    assert [p.name for p in await service.list(ALICE)] == ["自分用", "標準"]
    assert (await service.get(BOB, "標準")).is_team_template is True

    # 同じ名前で保存すると本人の観点になり、本人にはそちらが優先される
    await service.save(ALICE, "標準", "自分用に変えた", False)
    assert (await service.get(ALICE, "標準")).content == "自分用に変えた"
    assert (await service.get(BOB, "標準")).content == "チーム標準の観点"

    # 本人の観点を消すと、テンプレートが見える。テンプレート自体は消せない
    await service.delete(ALICE, "標準")
    assert (await service.get(ALICE, "標準")).is_team_template is True
    with pytest.raises(NotFound):
        await service.delete(ALICE, "標準")


async def test_default_perspective_switches(service: PerspectiveService) -> None:
    await service.save(ALICE, "A", "a", True)
    await service.save(ALICE, "B", "b", True)
    assert (await service.get(ALICE, None)).name == "B"
    with pytest.raises(NotFound):
        await service.get(BOB, None)


async def test_limit_per_user(service: PerspectiveService) -> None:
    for i in range(MAX_PERSPECTIVES_PER_USER):
        await service.save(ALICE, f"p{i}", "x", False)
    with pytest.raises(InvalidInput):
        await service.save(ALICE, "one-more", "x", False)
    # 上書きは件数に数えない。他の人には影響しない
    await service.save(ALICE, "p0", "updated", False)
    await service.save(BOB, "ok", "x", False)


async def test_invalid_input_and_users_are_rejected(service: PerspectiveService) -> None:
    with pytest.raises(InvalidInput):
        await service.save(ALICE, "", "x", False)
    with pytest.raises(Unauthenticated):
        await service.save(TEAM_OWNER, "x", "y", False)
    with pytest.raises(Unauthenticated):
        await service.list("")
