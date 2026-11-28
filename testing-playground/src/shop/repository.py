"""SQLite を使った永続化（component / integration test の対象）。"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass


class NotFoundError(Exception):
    pass


class OutOfStockError(Exception):
    pass


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: int
    stock: int


@dataclass(frozen=True)
class Order:
    id: int
    total: int
    items: list[tuple[int, int]]  # (product_id, quantity)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);
"""


class Repository:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._lock = threading.Lock()

    def close(self) -> None:
        self._conn.close()

    def add_product(self, name: str, price: int, stock: int) -> Product:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                (name, price, stock),
            )
        assert cur.lastrowid is not None
        return Product(id=cur.lastrowid, name=name, price=price, stock=stock)

    def get_product(self, product_id: int) -> Product:
        row = self._conn.execute(
            "SELECT id, name, price, stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"product {product_id} not found")
        return Product(*row)

    def create_order(self, items: list[tuple[int, int]], total: int) -> Order:
        """在庫を減らして注文を作る。1つでも在庫不足なら全体をロールバックする。"""
        with self._lock, self._conn:
            for product_id, quantity in items:
                cur = self._conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (quantity, product_id, quantity),
                )
                if cur.rowcount == 0:
                    # with self._conn により例外でロールバックされる
                    raise OutOfStockError(f"product {product_id} is out of stock")
            cur = self._conn.execute("INSERT INTO orders (total) VALUES (?)", (total,))
            order_id = cur.lastrowid
            assert order_id is not None
            self._conn.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                [(order_id, pid, qty) for pid, qty in items],
            )
        return Order(id=order_id, total=total, items=items)

    def get_order(self, order_id: int) -> Order:
        row = self._conn.execute(
            "SELECT id, total FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"order {order_id} not found")
        items = self._conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ? ORDER BY rowid",
            (order_id,),
        ).fetchall()
        return Order(id=row[0], total=row[1], items=[(p, q) for p, q in items])
