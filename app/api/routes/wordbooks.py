"""단어장 라우터 — 저장·조회·삭제 (핵심 루프의 '검수 화면' 데이터 공급).

추출 결과를 review 상태로 저장하고, 목록/상세 조회와 삭제를 제공한다.
검수 수정(PATCH)·확정(confirm)·자동완성은 다음 단계에서 추가한다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.firebase import get_current_uid
from app.models.wordbook import WordbookCreateRequest, WordbookDetail, WordbookSummary
from app.services.wordbooks import WordbookService, get_wordbook_service

router = APIRouter(prefix="/wordbooks", tags=["wordbooks"])


@router.post("", response_model=WordbookSummary, status_code=status.HTTP_201_CREATED)
async def create_wordbook(
    payload: WordbookCreateRequest,
    uid: Annotated[str, Depends(get_current_uid)],
    service: Annotated[WordbookService, Depends(get_wordbook_service)],
) -> WordbookSummary:
    return await service.create(owner_uid=uid, payload=payload)


@router.get("", response_model=list[WordbookSummary])
async def list_wordbooks(
    uid: Annotated[str, Depends(get_current_uid)],
    service: Annotated[WordbookService, Depends(get_wordbook_service)],
) -> list[WordbookSummary]:
    return await service.list_for_owner(uid)


@router.get("/{wordbook_id}", response_model=WordbookDetail)
async def get_wordbook(
    wordbook_id: str,
    uid: Annotated[str, Depends(get_current_uid)],
    service: Annotated[WordbookService, Depends(get_wordbook_service)],
) -> WordbookDetail:
    return await service.get_detail(owner_uid=uid, wordbook_id=wordbook_id)


@router.delete("/{wordbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wordbook(
    wordbook_id: str,
    uid: Annotated[str, Depends(get_current_uid)],
    service: Annotated[WordbookService, Depends(get_wordbook_service)],
) -> None:
    await service.delete(owner_uid=uid, wordbook_id=wordbook_id)
