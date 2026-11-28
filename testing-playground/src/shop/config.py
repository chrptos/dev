"""設定。環境変数 SHOP_* から読み込む（config test の対象）。"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHOP_")

    db_path: str = ":memory:"
    tax_rate_percent: int = Field(default=10, ge=0, le=100)
    # 割引コード -> "percent:10" / "fixed:500"
    discount_codes: dict[str, str] = Field(
        default_factory=lambda: {"WELCOME10": "percent:10", "OFF500": "fixed:500"}
    )
    max_quantity_per_item: int = Field(default=99, gt=0)
