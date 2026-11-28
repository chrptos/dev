"""注文金額の計算（純粋関数）。

金額はすべて「円の整数」で扱う。浮動小数点は使わない。
property-based test / mutation test の主な対象。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiscountKind(Enum):
    PERCENT = "percent"  # value: 0〜100 (%)
    FIXED = "fixed"  # value: 円


@dataclass(frozen=True)
class LineItem:
    unit_price: int
    quantity: int

    def __post_init__(self) -> None:
        if self.unit_price < 0:
            raise ValueError("unit_price must be >= 0")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")

    @property
    def amount(self) -> int:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class Discount:
    kind: DiscountKind
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("discount value must be >= 0")
        if self.kind is DiscountKind.PERCENT and self.value > 100:
            raise ValueError("percent discount must be <= 100")

    def apply(self, subtotal: int) -> int:
        """割引額を返す。割引額は小計を超えない。"""
        if self.kind is DiscountKind.FIXED:
            return min(self.value, subtotal)
        # 割引額は円未満を切り捨てる
        return min(subtotal * self.value // 100, subtotal)


@dataclass(frozen=True)
class Quote:
    subtotal: int
    discount: int
    tax: int
    total: int


def quote(
    items: list[LineItem],
    discount: Discount | None = None,
    tax_rate_percent: int = 10,
) -> Quote:
    """小計 → 割引 → 税（切り捨て）の順で計算する。"""
    if not items:
        raise ValueError("order must have at least one item")
    if not 0 <= tax_rate_percent <= 100:
        raise ValueError("tax_rate_percent must be between 0 and 100")

    subtotal = sum(item.amount for item in items)
    discount_amount = discount.apply(subtotal) if discount else 0
    taxable = subtotal - discount_amount
    tax = taxable * tax_rate_percent // 100
    return Quote(
        subtotal=subtotal,
        discount=discount_amount,
        tax=tax,
        total=taxable + tax,
    )
