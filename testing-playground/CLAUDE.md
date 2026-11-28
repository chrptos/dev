# CLAUDE.md（testing-playground）

検証手法を一通り試すための練習用プロジェクト。README.md のステージ表と「学びのメモ」を最新に保つ。

- パッケージ管理は uv。コマンドは `make` のターゲットを使う（`make all` が基本のチェック）。
- テストは手法ごとに `tests/<手法>/` に置く。新しい手法を足したら README の表と Makefile にも追加する。
- バグを直したら `tests/regression/` に再現テストを追加する。
- API を意図して変えたら `UPDATE_CONTRACT=1 uv run pytest tests/contract` でスナップショットを更新する。
- `src/shop/pricing.py` を変えたら `make mutation` で生き残りが 0 であることを確認する。
- CI の定義はリポジトリルートの `.github/workflows/testing-playground.yml`。
