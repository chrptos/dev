"""組み立て。どの実装を使うかを決めるのは、ここ（と seed.py）だけ。

起動: uv run uvicorn --factory job_posting_agent.main:create_app --reload
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from google.adk.models import BaseLlm
from google.adk.sessions import DatabaseSessionService
from sqlalchemy.ext.asyncio import AsyncEngine

from .application.conversation_service import ConversationService, MessageLimits
from .application.interfaces import Authenticator
from .application.job_posting_service import JobPostingService
from .application.perspective_service import PerspectiveService
from .application.services import AgentServices, HttpServices
from .application.summary_service import SummaryService
from .config import Settings, get_settings
from .infrastructure.adk.conversations import AdkConversationStore
from .infrastructure.adk.runner import AdkAgentRunner
from .infrastructure.auth import IapAuthenticator, LocalAuthenticator
from .infrastructure.db.engine import CloudSqlOptions, create_engine, create_tables, sessionmaker
from .infrastructure.rate_limit import InMemoryRateLimiter
from .infrastructure.repositories import (
    SqlJobPostingSource,
    SqlPerspectiveRepository,
    SqlSummaryRepository,
)
from .infrastructure.web_fetcher import SafeWebPageFetcher
from .presentation.agent.definition import build_agent
from .presentation.http.deps import HttpContext
from .presentation.http.errors import install_error_handlers
from .presentation.http.routes import router
from .presentation.http.static import mount_frontend


def build_engine(settings: Settings) -> AsyncEngine:
    cloud_sql = None
    if settings.cloud_sql_instance:
        cloud_sql = CloudSqlOptions(
            instance=settings.cloud_sql_instance,
            iam_user=settings.db_iam_user,
            db_name=settings.db_name,
            ip_type=settings.cloud_sql_ip_type,
        )
    return create_engine(settings.database_url, cloud_sql)


def build_authenticator(settings: Settings) -> Authenticator:
    if settings.auth_mode == "local":
        return LocalAuthenticator(settings.local_user)
    return IapAuthenticator(settings.iap_audience or "")


def build_agent_services(engine: AsyncEngine, settings: Settings) -> AgentServices:
    sessions = sessionmaker(engine)
    return AgentServices(
        job_postings=JobPostingService(
            SqlJobPostingSource(sessions),
            SafeWebPageFetcher(
                max_bytes=settings.url_fetch_max_bytes,
                timeout=settings.url_fetch_timeout_seconds,
            ),
        ),
        summaries=SummaryService(SqlSummaryRepository(sessions)),
        perspectives=PerspectiveService(SqlPerspectiveRepository(sessions)),
    )


@dataclass
class _Resources:
    engine: AsyncEngine
    runner: AdkAgentRunner


def create_app(
    settings: Settings | None = None,
    *,
    model: str | BaseLlm | None = None,
    authenticator: Authenticator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    # 設定が足りなければ、起動の時点で止める（IAP_AUDIENCE がないまま公開しない）
    auth = authenticator or build_authenticator(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(settings)
        await create_tables(engine)
        agent = build_agent(model or settings.gemini_model, build_agent_services(engine, settings))
        adk_sessions = DatabaseSessionService(db_engine=engine)
        runner = AdkAgentRunner(agent, adk_sessions)
        conversations = ConversationService(
            AdkConversationStore(adk_sessions),
            runner,
            InMemoryRateLimiter(settings.rate_limit_per_minute),
            MessageLimits(
                max_message_chars=settings.max_message_chars,
                max_upload_bytes=settings.max_upload_bytes,
            ),
        )
        app.state.http = HttpContext(
            services=HttpServices(conversations=conversations),
            authenticator=auth,
            upload_read_limit=settings.max_upload_bytes + 1,
        )
        resources = _Resources(engine=engine, runner=runner)
        try:
            yield
        finally:
            await resources.runner.close()
            await resources.engine.dispose()

    app = FastAPI(title="求人票エージェント", lifespan=lifespan, docs_url=None, redoc_url=None)
    install_error_handlers(app)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    if settings.frontend_dist:
        mount_frontend(app, settings.frontend_dist)
    return app
