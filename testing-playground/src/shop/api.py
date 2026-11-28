"""HTTP API（functional / acceptance / fuzz / contract test の対象）。

起動: uv run uvicorn shop.api:app --reload
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from pydantic import BaseModel, BeforeValidator, Field

from shop.config import Settings
from shop.pricing import Discount, DiscountKind, LineItem, quote
from shop.repository import NotFoundError, OutOfStockError, Repository

# ID の上限。fuzz test で次の2つが見つかったため、2^53-1 にしている:
# - SQLite の INTEGER（64bit）を超える ID で OverflowError -> 500
# - 2^63-1 をスキーマの maximum に書くと、JSON の数値（float）で 2^63 に丸められ、境界がずれる
MAX_ID = 2**53 - 1
IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]


def _reject_bool(v: object) -> object:
    # Pydantic は既定で true/false を 1/0 に変換するが、スキーマ上は integer ではない
    # （fuzz test が {"stock": false} の受理を契約違反として見つけた）
    if isinstance(v, bool):
        raise ValueError("boolean is not a valid integer")
    return v


Int = Annotated[int, BeforeValidator(_reject_bool)]


class StrictModel(BaseModel):
    pass


class ProductIn(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    price: Int = Field(ge=0, le=10_000_000)
    stock: Int = Field(ge=0, le=1_000_000)


class ProductOut(BaseModel):
    id: int
    name: str
    price: int
    stock: int


class OrderItem(StrictModel):
    product_id: Int = Field(ge=1, le=MAX_ID)
    quantity: Int = Field(ge=1)


class OrderIn(StrictModel):
    items: list[OrderItem] = Field(min_length=1, max_length=50)
    discount_code: str | None = None


class OrderOut(BaseModel):
    id: int
    subtotal: int
    discount: int
    tax: int
    total: int


class OrderDetail(BaseModel):
    id: int
    total: int
    items: list[OrderItem]


def parse_discount(spec: str) -> Discount:
    kind, _, value = spec.partition(":")
    return Discount(kind=DiscountKind(kind), value=int(value))


def get_repo(request: Request) -> Repository:
    repo: Repository = request.app.state.repo
    return repo


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


RepoDep = Annotated[Repository, Depends(get_repo)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="shop", version="0.1.0")
    app.state.settings = settings
    app.state.repo = Repository(settings.db_path)
    app.state.discounts = {
        code: parse_discount(spec) for code, spec in settings.discount_codes.items()
    }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/products", status_code=201, responses={400: {}, 422: {}})
    def add_product(body: ProductIn, repo: RepoDep) -> ProductOut:
        p = repo.add_product(body.name, body.price, body.stock)
        return ProductOut(id=p.id, name=p.name, price=p.price, stock=p.stock)

    @app.get("/products/{product_id}", responses={404: {}})
    def get_product(product_id: IdPath, repo: RepoDep) -> ProductOut:
        try:
            p = repo.get_product(product_id)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        return ProductOut(id=p.id, name=p.name, price=p.price, stock=p.stock)

    @app.post("/orders", status_code=201, responses={400: {}, 404: {}, 409: {}, 422: {}})
    def create_order(
        body: OrderIn, request: Request, repo: RepoDep, settings: SettingsDep
    ) -> OrderOut:
        for item in body.items:
            if item.quantity > settings.max_quantity_per_item:
                raise HTTPException(400, "quantity exceeds limit")

        discount = None
        if body.discount_code is not None:
            discount = request.app.state.discounts.get(body.discount_code)
            if discount is None:
                raise HTTPException(400, "unknown discount code")

        line_items = []
        for item in body.items:
            try:
                product = repo.get_product(item.product_id)
            except NotFoundError as e:
                raise HTTPException(404, str(e)) from e
            line_items.append(LineItem(unit_price=product.price, quantity=item.quantity))

        q = quote(line_items, discount, settings.tax_rate_percent)
        try:
            order = repo.create_order([(i.product_id, i.quantity) for i in body.items], q.total)
        except OutOfStockError as e:
            raise HTTPException(409, str(e)) from e
        return OrderOut(
            id=order.id, subtotal=q.subtotal, discount=q.discount, tax=q.tax, total=q.total
        )

    @app.get("/orders/{order_id}", responses={404: {}})
    def get_order(order_id: IdPath, repo: RepoDep) -> OrderDetail:
        try:
            o = repo.get_order(order_id)
        except NotFoundError as e:
            raise HTTPException(404, str(e)) from e
        return OrderDetail(
            id=o.id,
            total=o.total,
            items=[OrderItem(product_id=p, quantity=q) for p, q in o.items],
        )

    return app


app = create_app()
