"""헬스체크 스모크 테스트. 빌드 게이트가 앱 기동 가능성을 검증한다."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
