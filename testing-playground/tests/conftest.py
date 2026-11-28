from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shop.api import create_app
from shop.config import Settings


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings(db_path=":memory:"))


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
