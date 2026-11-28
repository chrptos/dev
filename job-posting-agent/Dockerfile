FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# 依存関係を先に入れて、コードだけ変えたときのビルドを速くする
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --create-home app
USER app

CMD ["sh", "-c", "exec /app/.venv/bin/uvicorn --factory job_posting_agent.server:create_app --host 0.0.0.0 --port ${PORT:-8080}"]
