"""求人票のまとめの型。どの入り口から来ても、この形にそろえる。"""

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["db", "pdf", "url", "text"]


class JobSummary(BaseModel):
    """求人票のまとめ。求人票に書かれていない項目は null か空のリストにし、推測で埋めない。"""

    company: str | None = Field(None, description="会社名")
    title: str | None = Field(None, description="職種・ポジション名")
    employment_type: str | None = Field(
        None, description="雇用形態（正社員、契約社員、業務委託など）"
    )
    location: str | None = Field(None, description="勤務地")
    remote_policy: str | None = Field(None, description="リモート可否や出社頻度")
    salary: str | None = Field(None, description="給与（求人票の表記のまま）")
    required_skills: list[str] = Field(default_factory=list, description="必須スキル・経験")
    preferred_skills: list[str] = Field(default_factory=list, description="歓迎スキル・経験")
    hiring_background: str | None = Field(None, description="募集背景")
    deadline: str | None = Field(None, description="応募締切")
    other_notes: str | None = Field(None, description="上の項目に入らない重要な情報")
    source_type: SourceType = Field(description="求人票の入手元: db / pdf / url / text")
    source_ref: str = Field(description="出典: 求人ID、PDF のファイル名、URL、または 'pasted'")
