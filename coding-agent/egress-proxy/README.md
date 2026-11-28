# egress-proxy（試作）

サンドボックスからの通信をすべて受けて、許可した宛先にだけ認証情報を付けて転送するプロキシです。設計は [../docs/design.md](../docs/design.md) の 6.3 を参照してください。

## 経路

| 経路 | 転送先 | 付ける認証情報 | 制限 |
|---|---|---|---|
| `/t/<task-token>/vertex/...` | Vertex AI（Claude） | Google のアクセストークン（ADC / メタデータサーバー） | 設定したプロジェクト、許可したモデル、`rawPredict` と `streamRawPredict` だけ。Claude Code 用 |
| `/t/<task-token>/anthropic/v1/messages` | Vertex AI（Claude） | 同上 | Anthropic Messages API の形を受け、本文の `model` を URL に移して Vertex の形に付け替える。許可したモデルだけ。Pi など用 |
| `/t/<task-token>/gemini/v1beta/models/<model>:<method>` | Vertex AI（Gemini、global） | 同上 | Gemini API の形を受け、Vertex の `publishers/google` に付け替える。`generateContent`、`streamGenerateContent`、`countTokens` と許可したモデルだけ。Pi など用 |
| `/t/<task-token>/github/<owner>/<repo>.git/...` | github.com | `GITHUB_TOKEN`（GitHub App のインストールトークンを想定） | タスクに許可したリポジトリの git smart HTTP だけ |
| `CONNECT <host>:443` | 公開レジストリ | なし | 許可したホストの 443 番ポートだけ。`Proxy-Authorization` にタスクトークンが必要 |
| それ以外 | — | — | すべて拒否 |

Vertex AI への応答からトークン数（入力、出力、キャッシュ）を集計してログに出します。ログにタスクトークンは出しません。

## 設定（環境変数）

| 変数 | 内容 | 既定値 |
|---|---|---|
| `VERTEX_PROJECT` | 転送を許可する GCP プロジェクト | 必須 |
| `TASKS_FILE` | タスクトークンとタスクの対応を書いた JSON | 必須 |
| `ALLOWED_MODELS` | 許可するモデル（カンマ区切り、`@` 以降のバージョンは無視） | `claude-sonnet-5-5,claude-haiku-5-5` |
| `ALLOWED_LOCATIONS` | 許可する Vertex AI のロケーション（カンマ区切り）。転送先のホスト名になるので決まった値だけを通す | `global,us,eu` |
| `REGISTRY_HOSTS` | CONNECT を許可するホスト（カンマ区切り） | npm、PyPI、Go のプロキシ |
| `GITHUB_TOKEN` | GitHub に付けるトークン | なし（付けない） |
| `LISTEN_ADDR` | 待ち受けるアドレス | `127.0.0.1:8080` |

`TASKS_FILE` の例（本番では受付 Bot が Firestore に登録する想定です）：

```json
{"<task-token>": {"id": "task-1", "repos": ["acme/app"]}}
```

## テスト

```bash
go test ./...
```

## サンドボックス側の設定

Claude Code：

```bash
export CLAUDE_CODE_USE_VERTEX=1
export CLAUDE_CODE_SKIP_VERTEX_AUTH=1
export ANTHROPIC_VERTEX_BASE_URL=http://<proxy>:8080/t/<task-token>/vertex
export ANTHROPIC_VERTEX_PROJECT_ID=<project>
export CLOUD_ML_REGION=global
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export HTTPS_PROXY=http://task:<task-token>@<proxy>:8080
```

Pi（`~/.pi/agent/models.json`、または `PI_CODING_AGENT_DIR` で指定した場所）：

```json
{"providers": {
  "proxy-claude": {"baseUrl": "http://<proxy>:8080/t/<task-token>/anthropic", "api": "anthropic-messages", "apiKey": "unused",
    "models": [{"id": "claude-sonnet-5-5", "reasoning": true, "contextWindow": 200000, "maxTokens": 32000}]},
  "proxy-gemini": {"baseUrl": "http://<proxy>:8080/t/<task-token>/gemini/v1beta", "api": "google-generative-ai", "apiKey": "unused",
    "models": [{"id": "gemini-2.5-flash", "reasoning": true, "contextWindow": 1000000, "maxTokens": 32000}]}
}}
```

`apiKey` はダミーです（プロキシが捨てて、自分のトークンに置き換えます）。あわせて `PI_OFFLINE=1`（pi.dev への起動時の通信を止める）と `HTTPS_PROXY` を設定します。

git：

```bash
git config --global url."http://<proxy>:8080/t/<task-token>/github/".insteadOf "https://github.com/"
```

## 制限

- CONNECT のトンネルの中は TLS なので、HTTP メソッドやパスは見えません。レジストリへの書き込み（publish）もプロキシでは止められません。
- push 先のブランチ名は検査しません。GitHub の Rulesets で `agent/*` に限る前提です。
- 試作のため、プロキシとサンドボックスの間は平文の HTTP です。本番では VPC 内に閉じたうえで、必要なら TLS にします。
