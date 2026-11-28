# バックエンドのコーディングアーキテクチャ

バックエンド（`backend/src/job_posting_agent/`）は、**疎結合なレイヤードアーキテクチャ**で書く。目的はレビューを楽にすること。差分がどの層にあるかを見れば、確かめるべきことが分かるようにする。

選んだ理由は [adr/0001-backend-layered-architecture.md](adr/0001-backend-layered-architecture.md) を参照。

## 1. 層と依存の向き

```
          seed（管理用のスクリプト。main の組み立て関数を使う）
                 ↓
          main（組み立て）
          ↓            ↓
   presentation    infrastructure     ← 同じ高さ。お互いを import しない
          ↓            ↓
          application（サービスとインターフェース）
                 ↓
          domain（型、エラー、決まりごと）
```

- 上の層は下の層を呼んでよい。下の層は上の層を知らない
- **infrastructure は application のインターフェース（`Protocol`）を実装する**。application は infrastructure を import しない（依存性の逆転）
- presentation と infrastructure はお互いを import しない。つなぐのは `main.py` だけ
- この向きは import-linter で確かめる（`pyproject.toml` の `[tool.importlinter]`）。違反すると `tests/test_architecture.py` が落ちる

## 2. 各層の役割

| 層 | 置くもの | import してよいもの | 置かないもの |
|---|---|---|---|
| `domain/` | 型（`UserId`、`JobSummary`、`Perspective`、`AgentEvent`）、エラー、決まりごと（文字数の上限など） | 標準ライブラリ、pydantic | FastAPI、ADK、google-genai、SQLAlchemy、httpx |
| `application/` | サービス（処理の手順）、インターフェース（`interfaces.py` の `Protocol`） | domain | FastAPI、ADK、google-genai、SQLAlchemy、httpx |
| `presentation/http/` | ルート、リクエストとレスポンスの形、エラーから HTTP ステータスへの変換、SSE への変換 | application、domain、FastAPI | SQL、ADK の Runner やセッション |
| `presentation/agent/` | AI に見せる指示文、ツール、エージェントの定義 | application、domain、ADK（`LlmAgent`、`ToolContext`） | SQL、ADK の Runner やセッション |
| `infrastructure/` | DB の接続とテーブル、リポジトリ、ADK の Runner とセッション、URL の取得、IAP の検証、回数制限の実装 | application、domain、外部ライブラリ | 処理の決まりごと |
| `main.py`、`seed.py` | 組み立て（どの実装を使うかを決める）、設定の読み込み | すべて | 処理の中身 |
| `config.py` | 設定（環境変数） | — | main と seed 以外からは import しない |

## 3. AI エージェントの置き場所

AI エージェントは、HTTP と並ぶ**もう1つの入口**として扱う。

| 部分 | 層 | 理由 |
|---|---|---|
| 指示文、ツール、エージェントの定義 | `presentation/agent/` | AI にとっての「画面」。AI が見るもの、呼べるものを決める |
| ADK の Runner を動かす処理 | `infrastructure/adk/runner.py` | 技術の詳細。`AgentRunner` の裏に隠す |
| 会話の保存（ADK のセッション） | `infrastructure/adk/conversations.py` | 技術の詳細。`ConversationStore` の裏に隠す |

ツールはサービスを呼ぶだけにする。**必ず守る決まりは指示文ではなくサービスに書く**。指示文に任せてよいのは「どのツールを、どの順で呼ぶか」の判断だけ。

## 4. 決まりごと（レビューのチェックリスト）

1. **利用者**：利用者を決めるのは `presentation/http/deps.py`（`current_user`）と、ツールの `tool_context.user_id` の2か所だけ。サービスは `UserId` を必ず引数で受け取り、`ensure_user` で確かめる
2. **SQL**：SQLAlchemy は `infrastructure/` の外で使わない。リポジトリはどのメソッドも持ち主（`owner`）で絞り込む
3. **決まりの場所**：文字数や件数の上限、持ち主の確認、回数制限、添付ファイルの確認はサービス（と domain）に書く。ルートとツールには書かない
4. **エラー**：サービスは `domain/errors.py` のエラーを投げる。HTTP ステータスへの変換は `presentation/http/errors.py`、ツールの戻り値への変換は `presentation/agent/tools.py` でだけ行う
5. **外部のデータ**：URL、PDF、DB の本文は、AI に渡すときに「信用しないデータ」として印を付ける（`untrusted_content`）
6. **設定**：`config.py` を読むのは `main.py` と `seed.py` だけ。他の層には、必要な値を引数で渡す
7. **ADK と Gemini**：ADK の Runner とセッションに触るのは `infrastructure/adk/` だけ

## 5. テストの置き場所

| 対象 | 置き場所 | 差し替えるもの |
|---|---|---|
| domain の決まり | `tests/domain/` | なし |
| サービス | `tests/application/` | インターフェースの偽物（`tests/fakes.py`） |
| リポジトリ、URL 取得、IAP、ADK | `tests/infrastructure/` | SQLite、`httpx.MockTransport`、手元で作った鍵 |
| ルートとツール | `tests/presentation/` | 偽のモデル（`ScriptedLlm`）と SQLite で端から端まで |
| 層の向き | `tests/test_architecture.py` | なし（import-linter を実行する） |

## 6. 新しい機能を足すときの手順

1. 型や決まりが要るなら `domain/` に足す
2. 処理の手順を `application/` のサービスに書く。外の技術が要るなら `interfaces.py` に `Protocol` を足す
3. `infrastructure/` でインターフェースを実装する
4. `presentation/` に入口（ルートかツール）を足す。サービスを呼ぶだけにする
5. `main.py` で組み立てる
6. それぞれの層のテストを書く
