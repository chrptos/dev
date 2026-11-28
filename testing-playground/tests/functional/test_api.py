"""Functional test: HTTP API を外から呼び、機能として正しく振る舞うかを確かめる。"""

from fastapi.testclient import TestClient


def _product(client: TestClient, price: int = 1000, stock: int = 10) -> int:
    r = client.post("/products", json={"name": "item", "price": price, "stock": stock})
    assert r.status_code == 201
    pid: int = r.json()["id"]
    return pid


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_order_returns_quote(client: TestClient) -> None:
    pid = _product(client, price=1000)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 201
    body = r.json()
    assert (body["subtotal"], body["discount"], body["tax"], body["total"]) == (2000, 0, 200, 2200)


def test_discount_code(client: TestClient) -> None:
    pid = _product(client, price=1000)
    r = client.post(
        "/orders",
        json={"items": [{"product_id": pid, "quantity": 1}], "discount_code": "WELCOME10"},
    )
    assert r.json()["total"] == 990


def test_unknown_discount_code(client: TestClient) -> None:
    pid = _product(client)
    r = client.post(
        "/orders", json={"items": [{"product_id": pid, "quantity": 1}], "discount_code": "NOPE"}
    )
    assert r.status_code == 400


def test_unknown_product(client: TestClient) -> None:
    r = client.post("/orders", json={"items": [{"product_id": 999, "quantity": 1}]})
    assert r.status_code == 404


def test_out_of_stock(client: TestClient) -> None:
    pid = _product(client, stock=1)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 2}]})
    assert r.status_code == 409


def test_quantity_limit(client: TestClient) -> None:
    pid = _product(client, stock=1000)
    r = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 100}]})
    assert r.status_code == 400


def test_validation_error(client: TestClient) -> None:
    r = client.post("/products", json={"name": "", "price": -1, "stock": 0})
    assert r.status_code == 422


def test_get_order(client: TestClient) -> None:
    pid = _product(client)
    oid = client.post("/orders", json={"items": [{"product_id": pid, "quantity": 3}]}).json()["id"]
    r = client.get(f"/orders/{oid}")
    assert r.status_code == 200
    assert r.json()["items"] == [{"product_id": pid, "quantity": 3}]
