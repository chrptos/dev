"""Component test: 1つの部品（Repository + 本物の SQLite）を単体で確かめる。"""

from collections.abc import Iterator

import pytest

from shop.repository import NotFoundError, OutOfStockError, Repository


@pytest.fixture
def repo() -> Iterator[Repository]:
    r = Repository(":memory:")
    yield r
    r.close()


def test_add_and_get_product(repo: Repository) -> None:
    p = repo.add_product("apple", 120, 5)
    assert repo.get_product(p.id) == p


def test_missing_product_raises(repo: Repository) -> None:
    with pytest.raises(NotFoundError):
        repo.get_product(999)


def test_order_decrements_stock(repo: Repository) -> None:
    p = repo.add_product("apple", 120, 5)
    order = repo.create_order([(p.id, 3)], total=396)
    assert repo.get_product(p.id).stock == 2
    assert repo.get_order(order.id).items == [(p.id, 3)]


def test_out_of_stock_rolls_back_whole_order(repo: Repository) -> None:
    a = repo.add_product("apple", 120, 5)
    b = repo.add_product("banana", 80, 1)
    with pytest.raises(OutOfStockError):
        repo.create_order([(a.id, 2), (b.id, 2)], total=0)
    # a の在庫も減っていないこと
    assert repo.get_product(a.id).stock == 5
    assert repo.get_product(b.id).stock == 1


def test_db_rejects_negative_price(repo: Repository) -> None:
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        repo.add_product("bad", -1, 1)


def test_data_survives_reopen(tmp_path: object) -> None:
    path = str(tmp_path) + "/shop.db"
    r1 = Repository(path)
    p = r1.add_product("apple", 120, 5)
    r1.close()
    r2 = Repository(path)
    assert r2.get_product(p.id).name == "apple"
    r2.close()
