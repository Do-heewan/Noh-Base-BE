"""앱 설정. 환경변수/.env 에서 로드한다 (pydantic-settings)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_name: str = "Noh Base BE"

    firebase_credentials_path: str = "./serviceAccountKey.json"
    firebase_project_id: str = ""
    firebase_storage_bucket: str = ""

    llm_api_key: str = ""

    # 무료 요금제: 비용 동인(변환 횟수) 기준 월 한도
    free_monthly_conversions: int = 5


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴. FastAPI 의존성으로 주입해 사용한다."""
    return Settings()
