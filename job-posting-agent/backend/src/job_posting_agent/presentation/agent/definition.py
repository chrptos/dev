"""エージェントの定義（指示文 + ツール）。動かすのは infrastructure/adk/runner.py。"""

from google.adk.agents import LlmAgent
from google.adk.models import BaseLlm

from ...application.services import AgentServices
from .instruction import INSTRUCTION
from .tools import build_tools

AGENT_NAME = "job_posting_agent"


def build_agent(model: str | BaseLlm, services: AgentServices) -> LlmAgent:
    return LlmAgent(
        name=AGENT_NAME,
        model=model,
        description="求人票をまとめ、利用者ごとの観点でネクストアクションを提案する",
        instruction=INSTRUCTION,
        tools=list(build_tools(services)),
    )
