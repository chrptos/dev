"""Acceptance test: ユーザーの要求（ストーリー）を Given / When / Then で書き、
受け入れ条件を満たしているかを確かめる。

ストーリー: 買い物客として、割引コードを使って注文し、在庫が正しく減ってほしい。
"""

from fastapi.testclient import TestClient


def test_customer_checks_out_with_discount_code(client: TestClient) -> None:
    # Given: 1000円の商品が在庫5個ある
    pid = client.post("/products", json={"name": "Tシャツ", "price": 1000, "stock": 5}).json()["id"]

    # When: 割引コード OFF500 を使って2個注文する
    r = client.post(
        "/orders",
        json={"items": [{"product_id": pid, "quantity": 2}], "discount_code": "OFF500"},
    )

    # Then: (2000 - 500) * 1.1 = 1650円になる
    assert r.status_code == 201
    assert r.json()["total"] == 1650
    # And: 在庫が3個になる
    assert client.get(f"/products/{pid}").json()["stock"] == 3


def test_customer_cannot_buy_more_than_stock(client: TestClient) -> None:
    # Given: 在庫が1個しかない
    pid = client.post("/products", json={"name": "限定品", "price": 5000, "stock": 1}).json()["id"]

    # When: 2個注文する
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})

    # Then: 注文は失敗し、在庫は変わらない
    assert r.status_code == 409
    assert client.get(f"/products/{pid}").json()["stock"] == 1
