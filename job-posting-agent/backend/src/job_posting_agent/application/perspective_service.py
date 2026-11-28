"""観点のサービス。本人の観点とチームのテンプレートを扱う。"""

from ..domain.errors import InvalidInput, NotFound
from ..domain.models import (
    MAX_PERSPECTIVES_PER_USER,
    TEAM_OWNER,
    Perspective,
    ensure_user,
    normalize_perspective,
)
from .interfaces import PerspectiveRepository


class PerspectiveService:
    def __init__(self, repository: PerspectiveRepository) -> None:
        self._repo = repository

    async def list(self, user: str) -> list[Perspective]:
        """本人の観点のあとに、チームのテンプレートを並べて返す。"""
        uid = ensure_user(user)
        return [*await self._repo.list_for(uid), *await self._repo.list_for(TEAM_OWNER)]

    async def get(self, user: str, name: str | None) -> Perspective:
        """名前で探す。本人の観点を優先し、なければチームのテンプレートを探す。

        name が None なら本人のデフォルトの観点を返す。
        """
        uid = ensure_user(user)
        found: Perspective | None
        if name is None:
            found = await self._repo.find_default(uid)
        else:
            found = await self._repo.find(uid, name) or await self._repo.find(TEAM_OWNER, name)
        if found is None:
            raise NotFound("観点が見つかりませんでした")
        return found

    async def save(self, user: str, name: str, content: str, make_default: bool) -> Perspective:
        """本人の観点を作るか上書きする。チームのテンプレートは変えられない。"""
        uid = ensure_user(user)
        name, content = normalize_perspective(name, content)
        saved = await self._repo.upsert(
            uid, name, content, make_default=make_default, max_per_owner=MAX_PERSPECTIVES_PER_USER
        )
        if saved is None:
            raise InvalidInput(f"観点は{MAX_PERSPECTIVES_PER_USER}件までです")
        return saved

    async def delete(self, user: str, name: str) -> None:
        if not await self._repo.delete(ensure_user(user), name.strip()):
            raise NotFound("その名前の観点はありません（チームのテンプレートは削除できません）")

    async def save_team_template(self, name: str, content: str) -> Perspective:
        """チーム共通のテンプレートを登録する。管理用のスクリプトからだけ呼ぶ。"""
        name, content = normalize_perspective(name, content)
        saved = await self._repo.upsert(
            TEAM_OWNER, name, content, make_default=False, max_per_owner=10_000
        )
        if saved is None:  # pragma: no cover - 上限を大きくしているので起きない
            raise InvalidInput("テンプレートを保存できませんでした")
        return saved
