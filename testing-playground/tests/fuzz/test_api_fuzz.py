"""Fuzz test + Contract test（API スキーマ）: Schemathesis が OpenAPI スキーマから
大量のリクエスト（境界値・不正値を含む）を自動生成して投げる。

確かめること:
- サーバーが 500 を返さないこと（not_a_server_error）
- レスポンスが OpenAPI に書いた形・ステータスコードと一致すること（契約を守っているか）
"""

from typing import Any

import schemathesis
from fastapi import FastAPI
from hypothesis import settings

from shop.api import create_app
from shop.config import Settings

app: FastAPI = create_app(Settings(db_path=":memory:"))
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
@settings(max_examples=50, deadline=None)
def test_api_conforms_to_schema(case: schemathesis.Case[Any]) -> None:
    case.call_and_validate()
