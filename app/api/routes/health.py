"""헬스체크 라우터. 빌드 게이트의 스모크 테스트 대상."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
