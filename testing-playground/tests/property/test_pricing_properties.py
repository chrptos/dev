"""Property-based test: 「どんな入力でも成り立つ性質」を Hypothesis で確かめる。

具体的な期待値の代わりに、不変条件（invariant）を書くのがポイント。
"""

from hypothesis import given
from hypothesis import strategies as st

from shop.pricing import Discount, DiscountKind, LineItem, quote

line_items = st.builds(
    LineItem,
    unit_price=st.integers(min_value=0, max_value=1_000_000),
    quantity=st.integers(min_value=1, max_value=1_000),
)
item_lists = st.lists(line_items, min_size=1, max_size=20)
discounts = st.one_of(
    st.none(),
    st.builds(Discount, kind=st.just(DiscountKind.PERCENT), value=st.integers(0, 100)),
    st.builds(Discount, kind=st.just(DiscountKind.FIXED), value=st.integers(0, 10_000_000)),
)
tax_rates = st.integers(min_value=0, max_value=100)


@given(item_lists, discounts, tax_rates)
def test_total_is_never_negative(items: list[LineItem], d: Discount | None, rate: int) -> None:
    assert quote(items, d, rate).total >= 0


@given(item_lists, discounts, tax_rates)
def test_discount_never_exceeds_subtotal(
    items: list[LineItem], d: Discount | None, rate: int
) -> None:
    q = quote(items, d, rate)
    assert 0 <= q.discount <= q.subtotal


@given(item_lists, discounts, tax_rates)
def test_parts_add_up_to_total(items: list[LineItem], d: Discount | None, rate: int) -> None:
    q = quote(items, d, rate)
    assert q.total == q.subtotal - q.discount + q.tax


@given(item_lists, discounts, tax_rates, st.randoms())
def test_item_order_does_not_matter(
    items: list[LineItem], d: Discount | None, rate: int, rnd: object
) -> None:
    shuffled = list(items)
    rnd.shuffle(shuffled)  # type: ignore[attr-defined]
    assert quote(items, d, rate) == quote(shuffled, d, rate)


@given(item_lists, tax_rates)
def test_discount_never_increases_total(items: list[LineItem], rate: int) -> None:
    without = quote(items, None, rate).total
    with_discount = quote(items, Discount(DiscountKind.PERCENT, 10), rate).total
    assert with_discount <= without


@given(item_lists, discounts)
def test_tax_is_monotonic_in_rate(items: list[LineItem], d: Discount | None) -> None:
    taxes = [quote(items, d, rate).tax for rate in range(0, 101, 10)]
    assert taxes == sorted(taxes)
