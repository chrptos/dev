"""Benchmark test: 処理時間を計測し、性能の劣化を検出する。

uv run pytest tests/benchmark --benchmark-only
# 基準を保存して比較する:
uv run pytest tests/benchmark --benchmark-only --benchmark-autosave
uv run pytest tests/benchmark --benchmark-only --benchmark-compare --benchmark-compare-fail=mean:20%
"""

from typing import Any

from fastapi.testclient import TestClient

from shop.pricing import Discount, DiscountKind, LineItem, quote

ITEMS = [LineItem(unit_price=i * 10, quantity=(i % 5) + 1) for i in range(1, 51)]


def test_quote_50_items(benchmark: Any) -> None:
    result = benchmark(quote, ITEMS, Discount(DiscountKind.PERCENT, 10), 10)
    assert result.total > 0


def test_create_order_endpoint(benchmark: Any, client: TestClient) -> None:
    pid = client.post("/products", json={"name": "b", "price": 100, "stock": 1_000_000}).json()[
        "id"
    ]
    body = {"items": [{"product_id": pid, "quantity": 1}]}

    r = benchmark(client.post, "/orders", json=body)
    assert r.status_code == 201
