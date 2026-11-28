"""Config test: 設定値の誤りを、デプロイ前に検出する。

本番障害の原因として「コードのバグ」と同じくらい多いのが「設定ミス」。
"""

import pytest
from pydantic import ValidationError

from shop.api import create_app, parse_discount
from shop.config import Settings


def test_defaults_are_valid() -> None:
    create_app(Settings())


@pytest.mark.parametrize("rate", ["-1", "101", "ten"])
def test_invalid_tax_rate_from_env_is_rejected(monkeypatch: pytest.MonkeyPatch, rate: str) -> None:
    monkeypatch.setenv("SHOP_TAX_RATE_PERCENT", rate)
    with pytest.raises(ValidationError):
        Settings()


def test_discount_codes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOP_DISCOUNT_CODES", '{"SUMMER": "percent:20"}')
    assert Settings().discount_codes == {"SUMMER": "percent:20"}


@pytest.mark.parametrize("spec", ["percent:200", "fixed:-1", "bogus:10", "percent:abc"])
def test_broken_discount_spec_fails_at_startup(spec: str) -> None:
    """壊れた割引設定は、リクエスト時ではなく起動時に失敗させる（fail fast）。"""
    with pytest.raises(ValueError):
        create_app(Settings(discount_codes={"BAD": spec}))


def test_parse_discount() -> None:
    d = parse_discount("fixed:500")
    assert d.value == 500
