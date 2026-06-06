"""FastAPI 진입점.

핵심 루프(입력→추출→자동완성→검수→학습)의 라우터는 기능 개발 시
app/api/routes/ 아래에 추가하고 여기서 include 한다.
"""

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
