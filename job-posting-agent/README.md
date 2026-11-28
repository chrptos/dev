# job-posting-agent

求人票（DB、PDF、Web URL、貼り付けたテキスト）を受け取り、決まった項目にまとめて、利用者ごとの観点でネクストアクションを提案するエージェントです。ADK で作り、Cloud Run と IAP で、許可した人だけに公開します。

設計は [docs/design.md](docs/design.md) を参照してください。

## ファイル構成

| パス | 内容 |
|---|---|
| `src/job_posting_agent/agent.py` | エージェントの定義とプロンプト |
| `src/job_posting_agent/tools.py` | エージェントのツール（利用者は `tool_context.user_id` から決める） |
| `src/job_posting_agent/repository.py` | 観点、求人のまとめ、求人票の読み書き |
| `src/job_posting_agent/url_fetch.py` | URL の安全な取得（社内や手元のアドレスへの接続を禁止する） |
| `src/job_posting_agent/auth.py` | IAP の JWT の検証 |
| `src/job_posting_agent/server.py` | チャット画面と API（FastAPI） |
| `src/job_posting_agent/static/index.html` | チャット画面 |
| `src/job_posting_agent/seed.py` | チーム共通の観点テンプレートの登録 |
| `adk_apps/job_posting_agent/` | `adk web` で試すための入り口 |

## ローカルで動かす

APIキーは使いません。自分の Google アカウント（ADC）で Vertex AI の Gemini を呼びます。

```bash
gcloud auth application-default login
```

```bash
cp .env.example .env
```

`.env` の `GOOGLE_CLOUD_PROJECT` を自分のプロジェクトにします。そのプロジェクトで Vertex AI の API を有効にし、自分のアカウントに `roles/aiplatform.user` を付けておきます。

```bash
uv sync
```

チームのテンプレートと、確認用の求人票 `J-001` を登録します。

```bash
uv run python -m job_posting_agent.seed --sample-job
```

チャット画面を起動して、http://localhost:8000 を開きます。

```bash
uv run uvicorn --factory job_posting_agent.server:create_app --reload
```

ツールの呼び出しを細かく見たいときは、ADK の開発用画面も使えます（利用者は見分けません）。

```bash
uv run adk web adk_apps
```

## テスト

Gemini は呼ばず、決まった返事をする偽のモデルで、Runner、セッション保存、ツールを通して確かめます。

```bash
uv run pytest
```

```bash
uv run ruff check . && uv run ruff format --check .
```

## Cloud Run にデプロイする

以下は手順の目安です。IAP を Cloud Run に直接かける機能のコマンドや IAP の JWT の `aud` の形は変わることがあるので、実行する前に公式ドキュメントで確認してください。`PROJECT_ID`、`REGION` などは置き換えてください。

### 1. API を有効にする

```bash
gcloud services enable run.googleapis.com aiplatform.googleapis.com sqladmin.googleapis.com iap.googleapis.com --project=PROJECT_ID
```

### 2. サービスアカウントを作り、権限を付ける

```bash
gcloud iam service-accounts create job-posting-agent --project=PROJECT_ID
```

```bash
for role in roles/aiplatform.user roles/cloudsql.client roles/cloudsql.instanceUser; do gcloud projects add-iam-policy-binding PROJECT_ID --member="serviceAccount:job-posting-agent@PROJECT_ID.iam.gserviceaccount.com" --role="$role"; done
```

キー（JSONファイル）は作りません。

### 3. Cloud SQL（PostgreSQL）を用意する

IAM 認証を有効にしたインスタンスを作り、サービスアカウントを DB のユーザーとして追加します。

```bash
gcloud sql instances create job-posting-db --database-version=POSTGRES_16 --region=REGION --tier=db-f1-micro --database-flags=cloudsql.iam_authentication=on --project=PROJECT_ID
```

```bash
gcloud sql databases create jobs --instance=job-posting-db --project=PROJECT_ID
```

```bash
gcloud sql users create job-posting-agent@PROJECT_ID.iam --instance=job-posting-db --type=cloud_iam_service_account --project=PROJECT_ID
```

DB のユーザーに、`jobs` データベースのテーブルを作る権限を付けます（Cloud SQL Studio などから `postgres` ユーザーで実行します）。`job_postings` を別のシステムが書き込む場合は、このアプリのユーザーには `SELECT` だけを許可してください。

```sql
GRANT ALL ON SCHEMA public TO "job-posting-agent@PROJECT_ID.iam";
```

### 4. デプロイする

まず IAP なしでデプロイし、IAP をかけてから `IAP_AUDIENCE` を設定します。`AUTH_MODE=iap` で `IAP_AUDIENCE` がないと起動しないので、最初のデプロイは失敗します。先に `IAP_AUDIENCE` を設定してデプロイしてもかまいません。

```bash
gcloud beta run deploy job-posting-agent --source . --region=REGION --project=PROJECT_ID --service-account=job-posting-agent@PROJECT_ID.iam.gserviceaccount.com --no-allow-unauthenticated --iap --set-env-vars=GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,AUTH_MODE=iap,IAP_AUDIENCE=/projects/PROJECT_NUMBER/locations/REGION/services/job-posting-agent,CLOUD_SQL_INSTANCE=PROJECT_ID:REGION:job-posting-db,DB_IAM_USER=job-posting-agent@PROJECT_ID.iam,DB_NAME=jobs
```

### 5. 使う人を追加する

```bash
gcloud beta iap web add-iam-policy-binding --resource-type=cloud-run --service=job-posting-agent --region=REGION --project=PROJECT_ID --member=user:MEMBER_EMAIL --role=roles/iap.httpsResourceAccessor
```

### 6. 仕上げ

- チームのテンプレートを登録する（Cloud Run ジョブか、Cloud SQL に接続できる環境から `python -m job_posting_agent.seed` を実行する）
- Model Armor のテンプレートを作り、Vertex AI の Gemini への入力と出力に適用する
- 予算アラートを設定する

## 環境変数

| 名前 | 既定値 | 内容 |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI` | なし | `TRUE` にして Vertex AI 経由で Gemini を使う |
| `GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION` | なし | Vertex AI のプロジェクトとリージョン |
| `GEMINI_MODEL` | `gemini-3.5-flash` | 使うモデル |
| `AUTH_MODE` | `iap` | `iap`（本番）か `local`（手元だけ） |
| `IAP_AUDIENCE` | なし | IAP の JWT の `aud`。`AUTH_MODE=iap` では必須 |
| `LOCAL_USER` | `local-user@example.com` | `AUTH_MODE=local` のときの利用者 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./local.db` | ローカルの DB |
| `CLOUD_SQL_INSTANCE` | なし | 設定すると Cloud SQL に IAM 認証で接続する（`project:region:instance`） |
| `CLOUD_SQL_IP_TYPE` | `public` | `public` か `private` |
| `DB_IAM_USER`、`DB_NAME` | なし、`jobs` | Cloud SQL の IAM ユーザーとデータベース名 |
| `RATE_LIMIT_PER_MINUTE` | `10` | 1人あたり1分間に送れるメッセージの数（インスタンスごと） |
| `MAX_UPLOAD_BYTES` | 10MB | 添付できる PDF の大きさの上限 |

## まだやっていないこと

- 返答の Markdown の表示に使う marked と DOMPurify を cdnjs から読み込んでいる。外部に依存したくなければ、`static/` に置いて配信する
- Docker イメージのビルドと Cloud Run へのデプロイの確認
- テーブルの形を変えるときのマイグレーション（今は起動時にテーブルを作るだけ）
- ネクストアクションの実行（今は提案だけ）
