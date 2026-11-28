"""Regression test: 一度起きたバグを再発させないためのテスト。

バグを直すたびに、そのバグを再現する最小のケースをここに追加する。
テスト名や docstring に、どのバグかを書いておく。
"""

from fastapi.testclient import TestClient

from shop.pricing import Discount, DiscountKind, LineItem, quote


def test_fixed_discount_larger_than_subtotal_does_not_make_total_negative() -> None:
    """（例）初期実装では min(amount, subtotal) がなく、合計がマイナスになっていた。"""
    q = quote([LineItem(100, 1)], Discount(DiscountKind.FIXED, 1000))
    assert q.total == 0


# ---- 以下は fuzz test（Schemathesis）が初回実行で見つけたバグ ----


def test_huge_id_returns_422_not_500(client: TestClient) -> None:
    """GET /products/9223372036854775808 で SQLite が OverflowError → 500 になっていた。"""
    assert client.get("/products/9007199254740992").status_code == 422
    assert client.get("/orders/9007199254740992").status_code == 422


def test_bool_is_not_accepted_as_int(client: TestClient) -> None:
    """{"stock": false} が 0 として受理され、API の契約（integer）に違反していた。"""
    r = client.post("/products", json={"name": "x", "price": 0, "stock": False})
    assert r.status_code == 422
