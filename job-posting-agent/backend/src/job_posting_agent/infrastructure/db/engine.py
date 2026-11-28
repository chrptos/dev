"""DB の接続。ローカルは SQLite、本番は Cloud SQL（IAM 認証）。"""

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .tables import Base


@dataclass(frozen=True)
class CloudSqlOptions:
    instance: str  # project:region:instance
    iam_user: str | None  # サービスアカウントなら sa-name@project.iam
    db_name: str
    ip_type: Literal["public", "private"] = "public"


def create_engine(database_url: str, cloud_sql: CloudSqlOptions | None = None) -> AsyncEngine:
    if cloud_sql is None:
        return create_async_engine(database_url)
    return create_async_engine("postgresql+asyncpg://", async_creator=_cloud_sql_creator(cloud_sql))


def _cloud_sql_creator(opts: CloudSqlOptions) -> Any:
    """パスワードを使わず、ADC（Cloud Run ではサービスアカウント）で IAM 認証する。

    コネクタはイベントループの中で作る必要があるので、最初の接続のときに作る。
    """
    from google.cloud.sql.connector import IPTypes, create_async_connector

    connector: Any = None
    lock = asyncio.Lock()

    async def getconn() -> Any:
        nonlocal connector
        async with lock:
            if connector is None:
                connector = await create_async_connector(
                    enable_iam_auth=True,
                    ip_type=IPTypes.PRIVATE if opts.ip_type == "private" else IPTypes.PUBLIC,
                )
        return await connector.connect_async(
            opts.instance, "asyncpg", user=opts.iam_user, db=opts.db_name
        )

    return getconn


async def create_tables(engine: AsyncEngine) -> None:
    """このアプリのテーブルを作る（あれば何もしない）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
