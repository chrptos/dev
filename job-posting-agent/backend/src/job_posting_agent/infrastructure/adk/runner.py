"""エージェントの実行（AgentRunner の実装）。

ADK の Runner を動かし、イベントをドメインの型に変える。
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from google.adk.agents import BaseAgent, RunConfig
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService
from google.genai import types

from ...domain.models import AgentEvent, AgentFailed, TextDelta, ToolCalled, UserId, UserMessage
from . import APP_NAME, ATTACHMENT_PREFIX, TITLE_KEY

logger = logging.getLogger(__name__)


class AdkAgentRunner:
    def __init__(self, agent: BaseAgent, sessions: BaseSessionService) -> None:
        self._runner = Runner(app_name=APP_NAME, agent=agent, session_service=sessions)

    async def close(self) -> None:
        await self._runner.close()

    async def run(
        self, user: UserId, conversation_id: str, message: UserMessage, new_title: str | None
    ) -> AsyncIterator[AgentEvent]:
        """部分的なテキストは少しずつ返し、まとめて届いたテキストは、部分を返していない
        ときだけ返す（同じ文章を2回表示しないため）。
        """
        streamed = ""
        try:
            async for event in self._runner.run_async(
                user_id=user,
                session_id=conversation_id,
                new_message=_content(message),
                state_delta={TITLE_KEY: new_title} if new_title else None,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                calls = event.get_function_calls()
                if event.partial:
                    if not calls:
                        chunk = _texts(event.content)
                        if chunk:
                            streamed += chunk
                            yield TextDelta(chunk)
                    continue
                for call in calls:
                    yield ToolCalled(call.name or "")
                final = _texts(event.content)
                if final and not streamed:
                    yield TextDelta(final)
                streamed = ""
        except Exception:
            logger.exception("エージェントの実行に失敗しました session=%s", conversation_id)
            yield AgentFailed("エラーが起きました。もう一度試してください")


def _content(message: UserMessage) -> types.Content:
    parts: list[types.Part] = []
    if message.text:
        parts.append(types.Part(text=message.text))
    if message.attachment is not None:
        a = message.attachment
        parts.append(types.Part(text=f"{ATTACHMENT_PREFIX}{a.filename}]"))
        parts.append(types.Part(inline_data=types.Blob(mime_type=a.mime_type, data=a.data)))
    return types.Content(role="user", parts=parts)


def _texts(content: Any) -> str:
    if content is None or not content.parts:
        return ""
    return "".join(p.text or "" for p in content.parts if p.text and not p.thought)
