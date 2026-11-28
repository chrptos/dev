"""adk web で手元から試すための入り口。

backend/ で、先に `uv run python -m job_posting_agent.seed --sample-job` でテーブルを作ってから、
`uv run adk web adk_apps` を実行する。
adk web は利用者を見分けないので、全員が同じ利用者として扱われる。手元での確認だけに使う。
"""

from job_posting_agent.config import get_settings
from job_posting_agent.main import build_agent_services, build_engine
from job_posting_agent.presentation.agent.definition import build_agent

_settings = get_settings()
root_agent = build_agent(
    _settings.gemini_model, build_agent_services(build_engine(_settings), _settings)
)
