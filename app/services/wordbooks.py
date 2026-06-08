"""단어장 저장·조회 비즈니스 로직.

레포지토리(Firestore)를 호출하고, 소유권 검증과 HTTP 오류 변환을 담당한다.
firebase-admin/Firestore 호출은 동기이므로 이벤트 루프를 막지 않도록 anyio.to_thread 로 감싼다.
"""

from __future__ import annotations

from typing import Annotated, Any

import anyio
from fastapi import Depends, HTTPException, status

from app.models.wordbook import (
    WordbookCreateRequest,
    WordbookDetail,
    WordbookSummary,
    WordRead,
)
from app.repositories.wordbooks import WordbookRepository, get_wordbook_repository


class WordbookService:
    """단어장 도메인 서비스."""

    def __init__(self, repo: WordbookRepository) -> None:
        self._repo = repo

    async def create(self, *, owner_uid: str, payload: WordbookCreateRequest) -> WordbookSummary:
        """검수 전(review) 단어장을 생성하고 요약을 반환한다."""
        wordbook_id = await anyio.to_thread.run_sync(
            lambda: self._repo.create(
                owner_uid=owner_uid,
                title=payload.title,
                source_type=payload.source_type,
                words=payload.words,
            )
        )
        # 서버 타임스탬프 등 실제 저장값을 반영해 반환한다.
        data = await anyio.to_thread.run_sync(self._repo.get, wordbook_id)
        if data is None:  # 방금 만든 문서가 사라지는 비정상 상황
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="단어장 생성 후 조회에 실패했습니다.",
            )
        return WordbookSummary.model_validate(data)

    async def list_for_owner(self, owner_uid: str) -> list[WordbookSummary]:
        """내 단어장 목록(최신순)."""
        rows = await anyio.to_thread.run_sync(self._repo.list_for_owner, owner_uid)
        return [WordbookSummary.model_validate(r) for r in rows]

    async def get_detail(self, *, owner_uid: str, wordbook_id: str) -> WordbookDetail:
        """단어장 + 단어 목록. 소유자가 아니면 404(존재 노출 금지)."""
        data = await self._get_owned(owner_uid=owner_uid, wordbook_id=wordbook_id)
        words = await anyio.to_thread.run_sync(self._repo.get_words, wordbook_id)
        return WordbookDetail.model_validate(
            {**data, "words": [WordRead.model_validate(w) for w in words]}
        )

    async def delete(self, *, owner_uid: str, wordbook_id: str) -> None:
        """단어장 삭제. 소유자가 아니면 404."""
        await self._get_owned(owner_uid=owner_uid, wordbook_id=wordbook_id)
        await anyio.to_thread.run_sync(self._repo.delete, wordbook_id)

    async def _get_owned(self, *, owner_uid: str, wordbook_id: str) -> dict[str, Any]:
        """문서를 읽고 소유권을 검증한다. 없거나 남의 것이면 404."""
        data = await anyio.to_thread.run_sync(self._repo.get, wordbook_id)
        if data is None or data.get("owner_uid") != owner_uid:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="단어장을 찾을 수 없습니다.",
            )
        return data


def get_wordbook_service(
    repo: Annotated[WordbookRepository, Depends(get_wordbook_repository)],
) -> WordbookService:
    """라우터에서 Depends 로 주입하는 서비스 팩토리."""
    return WordbookService(repo)
