"""エージェントの返答（ドメインのイベント）を、画面向けの SSE に変える。

イベントは delta / tool / error / done の4種類。フロントエンドの src/types.ts と合わせる。
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from ...domain.models import AgentEvent, AgentFailed, TextDelta, ToolCalled


def _line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def to_payload(event: AgentEvent) -> dict[str, Any]:
    match event:
        case TextDelta(text=text):
            return {"type": "delta", "text": text}
        case ToolCalled(name=name):
            return {"type": "tool", "name": name}
        case AgentFailed(message=message):
            return {"type": "error", "message": message}


async def to_sse(events: AsyncIterator[AgentEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield _line(to_payload(event))
    yield _line({"type": "done"})
