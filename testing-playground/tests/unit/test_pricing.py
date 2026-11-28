"""Unit test: 1つの関数を、具体的な入力と期待値で確かめる。"""

import re

import pytest

from shop.pricing import Discount, DiscountKind, LineItem, quote


def test_subtotal_is_sum_of_line_amounts() -> None:
    q = quote([LineItem(100, 2), LineItem(50, 1)], tax_rate_percent=0)
    assert q.subtotal == 250
    assert q.total == 250


def test_tax_is_rounded_down() -> None:
    # 99 * 10% = 9.9 -> 9
    q = quote([LineItem(99, 1)], tax_rate_percent=10)
    assert q.tax == 9
    assert q.total == 108


def test_percent_discount_is_applied_before_tax() -> None:
    q = quote([LineItem(1000, 1)], Discount(DiscountKind.PERCENT, 10), tax_rate_percent=10)
    assert q.discount == 100
    assert q.tax == 90
    assert q.total == 990


def test_fixed_discount_never_exceeds_subtotal() -> None:
    q = quote([LineItem(300, 1)], Discount(DiscountKind.FIXED, 500), tax_rate_percent=10)
    assert q.discount == 300
    assert q.total == 0


def test_empty_order_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"^order must have at least one item$"):
        quote([])


@pytest.mark.parametrize("rate", [-1, 101])
def test_invalid_tax_rate_is_rejected(rate: int) -> None:
    with pytest.raises(ValueError, match=r"^tax_rate_percent must be between 0 and 100$"):
        quote([LineItem(100, 1)], tax_rate_percent=rate)


@pytest.mark.parametrize(
    ("price", "qty", "message"),
    [(-1, 1, "unit_price must be >= 0"), (100, 0, "quantity must be > 0")],
)
def test_invalid_line_item_is_rejected(price: int, qty: int, message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        LineItem(price, qty)


@pytest.mark.parametrize(
    ("kind", "value", "message"),
    [
        (DiscountKind.PERCENT, 101, "percent discount must be <= 100"),
        (DiscountKind.PERCENT, -1, "discount value must be >= 0"),
        (DiscountKind.FIXED, -1, "discount value must be >= 0"),
    ],
)
def test_invalid_discount_is_rejected(kind: DiscountKind, value: int, message: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        Discount(kind, value)


# ---- mutation test で生き残った変異を殺すために追加したテスト ----


def test_default_tax_rate_is_10_percent() -> None:
    """変異: tax_rate_percent の既定値 10 -> 11 が検出されていなかった。"""
    assert quote([LineItem(1000, 1)]).tax == 100


def test_amounts_are_integers_not_floats() -> None:
    """変異: // -> / が検出されていなかった（1000.0 == 1000 が True になるため）。"""
    q = quote([LineItem(999, 1)], Discount(DiscountKind.PERCENT, 10))
    assert all(type(v) is int for v in (q.subtotal, q.discount, q.tax, q.total))


def test_boundary_values_are_accepted() -> None:
    assert LineItem(0, 1).amount == 0
    assert Discount(DiscountKind.PERCENT, 100).apply(1000) == 1000
    assert Discount(DiscountKind.PERCENT, 0).apply(1000) == 0
    assert quote([LineItem(100, 1)], tax_rate_percent=0).tax == 0
    assert quote([LineItem(100, 1)], tax_rate_percent=100).tax == 100
