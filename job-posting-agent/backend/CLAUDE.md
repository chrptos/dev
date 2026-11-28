# CLAUDE.md（job-posting-agent/backend）

FastAPI と ADK で書いた、求人票エージェントのバックエンド。**疎結合なレイヤードアーキテクチャ**で書く。詳しくは `../docs/backend-architecture.md`、選んだ理由は `../docs/adr/0001-backend-layered-architecture.md`。

## 層と import の向き

```
seed → main → presentation | infrastructure → application → domain
```

- `domain/`：型、エラー、決まりごと。FastAPI、ADK、google-genai、SQLAlchemy、httpx を import しない
- `application/`：サービスとインターフェース（`interfaces.py` の `Protocol`）。domain だけを import する
- `presentation/http/`：ルート。サービスを呼んで結果を返すだけ
- `presentation/agent/`：AI の指示文とツール。ツールはサービスを呼ぶだけ
- `infrastructure/`：インターフェースの実装（SQL、ADK の Runner とセッション、URL 取得、IAP）
- `main.py`：組み立て。`config.py` を読むのは `main.py` と `seed.py` だけ

presentation と infrastructure はお互いを import しない。

## コードを書くときの決まり

1. 利用者を決めるのは `presentation/http/deps.py` の `current_user` と、ツールの `tool_context.user_id` だけ。サービスは利用者を引数で受け取り、`ensure_user` で確かめる
2. 必ず守る決まり（持ち主の確認、上限、回数制限、添付ファイルの確認）はサービスか domain に書く。ルート、ツール、指示文には書かない
3. SQL と SQLAlchemy は `infrastructure/` だけ。リポジトリのどのメソッドも持ち主で絞り込む
4. エラーは `domain/errors.py` のものを投げる。HTTP ステータスへの変換は `presentation/http/errors.py`、ツールの戻り値への変換は `presentation/agent/tools.py` だけ
5. URL、PDF、DB の本文を AI に渡すときは `untrusted_content` として印を付ける
6. ADK の Runner とセッション（`google.adk.runners`、`google.adk.sessions`）を使うのは `infrastructure/adk/` だけ

## 新しい機能を足す手順

domain（型と決まり）→ application（サービスと、必要なら `Protocol`）→ infrastructure（実装）→ presentation（ルートかツール）→ main（組み立て）→ 各層のテスト。

## テスト

- `tests/domain/`、`tests/application/`（`tests/fakes.py` の偽物を使う）、`tests/infrastructure/`、`tests/presentation/`（`ScriptedLlm` と SQLite で端から端まで）に分ける
- 層の向きは `tests/test_architecture.py` が import-linter で確かめる

変更したら、次がすべて通ることを確かめる。

```bash
uv run pytest && uv run ruff check . && uv run ruff format --check .
```
