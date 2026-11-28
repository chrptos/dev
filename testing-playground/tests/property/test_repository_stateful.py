"""Stateful property-based test: 操作の「列」をランダムに生成し、
実装（SQLite）と単純なモデル（dict）の状態が常に一致するかを確かめる。
"""

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from shop.repository import OutOfStockError, Repository


class InventoryMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.repo = Repository(":memory:")
        self.model: dict[int, int] = {}  # product_id -> stock

    @rule(stock=st.integers(0, 50))
    def add_product(self, stock: int) -> None:
        p = self.repo.add_product("p", 100, stock)
        self.model[p.id] = stock

    @precondition(lambda self: bool(self.model))
    @rule(data=st.data())
    def order(self, data: st.DataObject) -> None:
        ids = list(self.model)
        items = data.draw(
            st.lists(
                st.tuples(st.sampled_from(ids), st.integers(1, 20)),
                min_size=1,
                max_size=3,
                unique_by=lambda t: t[0],
            )
        )
        enough = all(self.model[pid] >= qty for pid, qty in items)
        try:
            self.repo.create_order(items, total=0)
        except OutOfStockError:
            assert not enough
            return  # 全体がロールバックされ、モデルも変えない
        assert enough
        for pid, qty in items:
            self.model[pid] -= qty

    @invariant()
    def stock_matches_model(self) -> None:
        for pid, stock in self.model.items():
            assert self.repo.get_product(pid).stock == stock

    @invariant()
    def stock_is_never_negative(self) -> None:
        assert all(s >= 0 for s in self.model.values())

    def teardown(self) -> None:
        self.repo.close()


TestInventory = InventoryMachine.TestCase
