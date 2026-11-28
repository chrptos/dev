# 1. フロントエンドをビルドする
FROM node:24-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2. バックエンドに、ビルドした画面を同梱する
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 FRONTEND_DIST=/app/frontend-dist

# 依存関係を先に入れて、コードだけ変えたときのビルドを速くする
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src ./src
RUN uv sync --frozen --no-dev
COPY --from=frontend /frontend/dist ./frontend-dist

RUN useradd --create-home app
USER app

CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn --factory job_posting_agent.server:create_app --host 0.0.0.0 --port ${PORT:-8080}"]
