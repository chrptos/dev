"""adk web で手元から試すための入り口。

backend/ で `uv run adk web adk_apps` を実行する。
adk web は利用者を見分けないので、全員が同じ利用者として扱われる。手元での確認だけに使う。
"""

from job_posting_agent.agent import build_agent

root_agent = build_agent()
