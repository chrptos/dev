# Pre-production の検証をまとめて実行するためのショートカット
.PHONY: all lint typecheck security test unit property component functional acceptance \
        regression contract fuzz config coverage bench mutation smoke serve

all: lint typecheck security coverage

lint:            ## Lint / format チェック
	uv run ruff check .
	uv run ruff format --check .

typecheck:       ## Static analysis（型）
	uv run mypy

security:        ## Static analysis（セキュリティ）
	uv run bandit -c pyproject.toml -r src

test:            ## benchmark と smoke 以外の全テスト
	uv run pytest

unit:        ; uv run pytest tests/unit
property:    ; uv run pytest tests/property
component:   ; uv run pytest tests/component
functional:  ; uv run pytest tests/functional
acceptance:  ; uv run pytest tests/acceptance
regression:  ; uv run pytest tests/regression
contract:    ; uv run pytest tests/contract
fuzz:        ; uv run pytest tests/fuzz
config:      ; uv run pytest tests/config

coverage:        ## 全テスト + カバレッジ（90% 未満なら失敗）
	uv run pytest --cov --cov-report=term-missing

bench:           ## Benchmark
	uv run pytest tests/benchmark --benchmark-only

mutation:        ## Mutation test（時間がかかる）
	uv run mutmut run; uv run mutmut results

serve:           ## 開発サーバー起動
	uv run uvicorn shop.api:app --reload

smoke:           ## 起動中のサーバーに smoke test（別ターミナルで make serve）
	SHOP_BASE_URL=http://127.0.0.1:8000 uv run pytest tests/smoke
