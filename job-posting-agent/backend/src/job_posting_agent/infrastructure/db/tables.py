"""テーブル定義。ADK のセッションのテーブルは ADK が作る。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class JobPostingRow(Base):
    """求人票の元データ。チーム全員が読める。このアプリからは読むだけ。"""

    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company: Mapped[str | None] = mapped_column(String(200))
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(2000))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class JobSummaryRow(Base):
    """エージェントがまとめた求人票。まとめた本人だけが読める。"""

    __tablename__ = "job_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(320), index=True)
    source_type: Mapped[str] = mapped_column(String(16))
    source_ref: Mapped[str] = mapped_column(String(2000))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PerspectiveRow(Base):
    """ネクストアクションを考えるときの観点。本人のものと、チーム共通のテンプレートがある。"""

    __tablename__ = "perspectives"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
