"""入口（HTTP、AI のツール）に渡すサービスのまとまり。"""

from dataclasses import dataclass

from .conversation_service import ConversationService
from .job_posting_service import JobPostingService
from .perspective_service import PerspectiveService
from .summary_service import SummaryService


@dataclass(frozen=True)
class AgentServices:
    """AI のツールから使うサービス。"""

    job_postings: JobPostingService
    summaries: SummaryService
    perspectives: PerspectiveService


@dataclass(frozen=True)
class HttpServices:
    """HTTP の入口から使うサービス。"""

    conversations: ConversationService
