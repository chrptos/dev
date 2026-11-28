"""データベースの接続とテーブル定義。

ADK のセッションと、このアプリのテーブル（観点、求人のまとめ、求人票）は同じ DB に置く。
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import Settings, get_settings

# チーム共通の観点テンプレートの持ち主。IAP のメールアドレスとは重ならない
TEAM_OWNER = "__team__"


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class JobPosting(Base):
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


class Perspective(Base):
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


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None
_lock = asyncio.Lock()


async def _create_engine(settings: Settings) -> AsyncEngine:
    if settings.cloud_sql_instance:
        # パスワードを使わず、ADC（Cloud Run ではサービスアカウント）で IAM 認証する
        from google.cloud.sql.connector import IPTypes, create_async_connector

        connector = await create_async_connector(
            enable_iam_auth=True,
            ip_type=IPTypes.PRIVATE if settings.cloud_sql_ip_type == "private" else IPTypes.PUBLIC,
        )
        instance = settings.cloud_sql_instance

        async def getconn() -> Any:
            return await connector.connect_async(
                instance, "asyncpg", user=settings.db_iam_user, db=settings.db_name
            )

        return create_async_engine("postgresql+asyncpg://", async_creator=getconn)
    return create_async_engine(settings.database_url)


async def get_engine() -> AsyncEngine:
    """接続を1つだけ作り、初回にこのアプリのテーブルを作る。"""
    global _engine, _sessionmaker
    if _engine is None:
        async with _lock:
            if _engine is None:
                engine = await _create_engine(get_settings())
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
                _engine = engine
    return _engine


async def use_engine(engine: AsyncEngine) -> None:
    """テストなどで、決まったエンジンを使う。"""
    global _engine, _sessionmaker
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _engine = engine
    _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session() -> AsyncIterator[AsyncSession]:
    await get_engine()
    if _sessionmaker is None:
        raise RuntimeError("データベースに接続できていません")
    async with _sessionmaker() as s:
        yield s
