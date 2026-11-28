"""ビルドしたフロントエンド（frontend/dist）の配信。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, dist: str) -> None:
    """API より後に呼ぶ。そうすると /api や /healthz が優先される。"""
    path = Path(dist)
    if not (path / "index.html").is_file():
        raise RuntimeError(f"FRONTEND_DIST に index.html がありません: {path}")
    app.mount("/", StaticFiles(directory=path, html=True), name="frontend")
