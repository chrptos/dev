"""Contract test（スナップショット）: API の「約束」をファイルに固定し、
意図しない破壊的変更（フィールド削除・型変更など）を検出する。

意図して API を変えたときは、スナップショットを更新する:
    UPDATE_CONTRACT=1 uv run pytest tests/contract
"""

import json
import os
from pathlib import Path

from shop.api import create_app
from shop.config import Settings

SNAPSHOT = Path(__file__).parent / "openapi.snapshot.json"


def test_openapi_matches_snapshot() -> None:
    current = create_app(Settings()).openapi()
    if os.environ.get("UPDATE_CONTRACT") or not SNAPSHOT.exists():
        SNAPSHOT.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    expected = json.loads(SNAPSHOT.read_text())
    assert current == expected, "API contract changed. Run with UPDATE_CONTRACT=1 if intended."
