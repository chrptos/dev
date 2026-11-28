"""Smoke test: 起動中のサーバーに対して「最低限動くか」だけを素早く確かめる。

デプロイ直後に実行する想定。SHOP_BASE_URL が無ければ skip する。
    SHOP_BASE_URL=http://127.0.0.1:8000 uv run pytest tests/smoke
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("SHOP_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE_URL, reason="SHOP_BASE_URL is not set")


def test_health() -> None:
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200


def test_can_create_product_and_order() -> None:
    p = httpx.post(
        f"{BASE_URL}/products", json={"name": "smoke", "price": 1, "stock": 1}, timeout=5
    )
    assert p.status_code == 201
    o = httpx.post(
        f"{BASE_URL}/orders",
        json={"items": [{"product_id": p.json()["id"], "quantity": 1}]},
        timeout=5,
    )
    assert o.status_code == 201
