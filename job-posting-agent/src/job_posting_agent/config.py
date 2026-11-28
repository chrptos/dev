"""環境変数から読み込む設定。"""

from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Gemini のモデル名。Vertex AI 経由で使うかどうかは GOOGLE_GENAI_USE_VERTEXAI で決まる
    gemini_model: str = "gemini-3.5-flash"

    # iap: IAP の JWT を検証して利用者を決める（本番）
    # local: LOCAL_USER を利用者として扱う（手元での開発だけ）
    auth_mode: Literal["iap", "local"] = "iap"
    local_user: str = "local-user@example.com"
    # IAP の JWT の aud。Cloud Run に直接 IAP をかけた場合は
    # /projects/PROJECT_NUMBER/locations/REGION/services/SERVICE_NAME の形
    iap_audience: str | None = None

    # ローカルは SQLite。CLOUD_SQL_INSTANCE を設定すると Cloud SQL に IAM 認証で接続する
    database_url: str = "sqlite+aiosqlite:///./local.db"
    cloud_sql_instance: str | None = None  # project:region:instance
    cloud_sql_ip_type: Literal["public", "private"] = "public"
    db_iam_user: str | None = None  # サービスアカウントなら sa-name@project.iam
    db_name: str = "jobs"

    rate_limit_per_minute: int = 10
    max_upload_bytes: int = 10 * 1024 * 1024
    max_message_chars: int = 20_000
    url_fetch_max_bytes: int = 2 * 1024 * 1024
    url_fetch_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    # GOOGLE_GENAI_USE_VERTEXAI などは google-genai が os.environ から読むので、
    # .env を環境変数として読み込んでおく（すでに設定された値は上書きしない）
    load_dotenv()
    return Settings()
