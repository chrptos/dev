"""データベースの読み書き。

どの関数も owner_id を必ず受け取り、その人のデータ（とチームのテンプレート）だけを扱う。
owner_id はサーバーが IAP から決めた値で、AI が決めた値ではない。
"""

import uuid
from typing import Any

from sqlalchemy import delete, select, update

from . import db
from .db import TEAM_OWNER, JobPosting, JobSummaryRow, Perspective
from .schemas import JobSummary

MAX_PERSPECTIVE_NAME = 50
MAX_PERSPECTIVE_CONTENT = 2000
MAX_PERSPECTIVES_PER_USER = 30


class RepositoryError(ValueError):
    """利用者に伝えてよい、入力の誤り。"""


def _check_owner(owner_id: str) -> None:
    if not owner_id or owner_id == TEAM_OWNER:
        raise RepositoryError("利用者を特定できません")


# --- 求人票（元データ） ---


async def get_job_posting(job_id: str) -> dict[str, Any] | None:
    async with db.session() as s:
        row = await s.get(JobPosting, job_id)
        if row is None:
            return None
        return {
            "id": row.id,
            "company": row.company,
            "title": row.title,
            "body": row.body,
            "url": row.url,
        }


# --- 求人のまとめ ---


async def save_summary(owner_id: str, summary: JobSummary) -> str:
    _check_owner(owner_id)
    summary_id = str(uuid.uuid4())
    async with db.session() as s:
        s.add(
            JobSummaryRow(
                id=summary_id,
                owner_id=owner_id,
                source_type=summary.source_type,
                source_ref=summary.source_ref[:2000],
                data=summary.model_dump(),
            )
        )
        await s.commit()
    return summary_id


async def list_summaries(owner_id: str, limit: int = 20) -> list[dict[str, Any]]:
    _check_owner(owner_id)
    async with db.session() as s:
        rows = await s.scalars(
            select(JobSummaryRow)
            .where(JobSummaryRow.owner_id == owner_id)
            .order_by(JobSummaryRow.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": r.id,
                "company": r.data.get("company"),
                "title": r.data.get("title"),
                "source_type": r.source_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]


async def get_summary(owner_id: str, summary_id: str) -> dict[str, Any] | None:
    _check_owner(owner_id)
    async with db.session() as s:
        row = await s.scalar(
            select(JobSummaryRow).where(
                JobSummaryRow.id == summary_id, JobSummaryRow.owner_id == owner_id
            )
        )
        return None if row is None else {"id": row.id, **row.data}


# --- 観点 ---


def _perspective_dict(p: Perspective) -> dict[str, Any]:
    return {
        "name": p.name,
        "content": p.content,
        "is_default": p.is_default,
        "is_team_template": p.owner_id == TEAM_OWNER,
    }


async def list_perspectives(owner_id: str) -> list[dict[str, Any]]:
    """本人の観点と、チームのテンプレートを返す。"""
    _check_owner(owner_id)
    async with db.session() as s:
        rows = await s.scalars(
            select(Perspective)
            .where(Perspective.owner_id.in_([owner_id, TEAM_OWNER]))
            .order_by(Perspective.owner_id == TEAM_OWNER, Perspective.name)
        )
        return [_perspective_dict(p) for p in rows]


async def get_perspective(owner_id: str, name: str | None = None) -> dict[str, Any] | None:
    """名前で観点を探す。本人の観点を優先し、なければチームのテンプレートを探す。

    name を省くと、本人のデフォルトの観点を返す。
    """
    _check_owner(owner_id)
    async with db.session() as s:
        if name is None:
            row = await s.scalar(
                select(Perspective).where(
                    Perspective.owner_id == owner_id, Perspective.is_default.is_(True)
                )
            )
            return None if row is None else _perspective_dict(row)
        for owner in (owner_id, TEAM_OWNER):
            row = await s.scalar(
                select(Perspective).where(Perspective.owner_id == owner, Perspective.name == name)
            )
            if row is not None:
                return _perspective_dict(row)
        return None


async def save_perspective(
    owner_id: str, name: str, content: str, make_default: bool = False
) -> dict[str, Any]:
    """本人の観点を作るか上書きする。チームのテンプレートは変えられない。"""
    _check_owner(owner_id)
    name = name.strip()
    content = content.strip()
    if not name or len(name) > MAX_PERSPECTIVE_NAME:
        raise RepositoryError(f"観点の名前は1〜{MAX_PERSPECTIVE_NAME}文字にしてください")
    if not content or len(content) > MAX_PERSPECTIVE_CONTENT:
        raise RepositoryError(f"観点の内容は1〜{MAX_PERSPECTIVE_CONTENT}文字にしてください")

    async with db.session() as s:
        row = await s.scalar(
            select(Perspective).where(Perspective.owner_id == owner_id, Perspective.name == name)
        )
        if row is None:
            count = len(
                (
                    await s.scalars(select(Perspective.id).where(Perspective.owner_id == owner_id))
                ).all()
            )
            if count >= MAX_PERSPECTIVES_PER_USER:
                raise RepositoryError(f"観点は{MAX_PERSPECTIVES_PER_USER}件までです")
            row = Perspective(owner_id=owner_id, name=name, content=content, is_default=False)
            s.add(row)
        else:
            row.content = content
        if make_default:
            await s.execute(
                update(Perspective).where(Perspective.owner_id == owner_id).values(is_default=False)
            )
            row.is_default = True
        await s.commit()
        return _perspective_dict(row)


async def delete_perspective(owner_id: str, name: str) -> bool:
    _check_owner(owner_id)
    async with db.session() as s:
        result = await s.execute(
            delete(Perspective).where(Perspective.owner_id == owner_id, Perspective.name == name)
        )
        await s.commit()
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]


async def save_team_template(name: str, content: str) -> None:
    """チーム共通のテンプレートを登録する。管理用のスクリプトからだけ呼ぶ。"""
    async with db.session() as s:
        row = await s.scalar(
            select(Perspective).where(Perspective.owner_id == TEAM_OWNER, Perspective.name == name)
        )
        if row is None:
            s.add(Perspective(owner_id=TEAM_OWNER, name=name, content=content, is_default=False))
        else:
            row.content = content
        await s.commit()
