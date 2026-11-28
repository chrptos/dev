import asyncio
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import Any

import pytest
from google.adk.models import BaseLlm, LlmRequest, LlmResponse
from google.genai import types
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from job_posting_agent.infrastructure.db.engine import create_engine, create_tables, sessionmaker


class ScriptedLlm(BaseLlm):
    """決まった返事を順に返す偽のモデル。Gemini を呼ばずに Runner を通して試すために使う。"""

    model: str = "scripted"
    script: list[types.Content] = Field(default_factory=list)
    requests: list[LlmRequest] = Field(default_factory=list)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.requests.append(llm_request)
        content = (
            self.script.pop(0)
            if self.script
            else types.Content(role="model", parts=[types.Part(text="（台本の終わり）")])
        )
        yield LlmResponse(content=content)


def text_reply(text: str) -> types.Content:
    return types.Content(role="model", parts=[types.Part(text=text)])


def call_reply(name: str, args: dict[str, Any]) -> types.Content:
    return types.Content(
        role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """テストごとに空の SQLite を使う。"""
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def sessions(db_url: str) -> Iterator[async_sessionmaker[AsyncSession]]:
    engine = create_engine(db_url)
    asyncio.run(create_tables(engine))
    yield sessionmaker(engine)
    asyncio.run(engine.dispose())
