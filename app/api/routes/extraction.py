"""PDF 추출 라우터.

POST /extract/pdf — 업로드한 디지털 PDF에서 (영어 표제어, 뜻)을 verbatim 추출해 반환.
검수 화면이 이 결과를 받아 사용자가 확인·수정한다. (Firestore 저장은 별도 단계)
"""

from __future__ import annotations

from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.firebase import get_current_uid
from app.models.extraction import ExtractionResult
from app.services.pdf_extraction import extract_from_pdf

router = APIRouter(prefix="/extract", tags=["extraction"])

_MAX_BYTES = 20 * 1024 * 1024  # 20MB


@router.post("/pdf", response_model=ExtractionResult)
async def extract_pdf(
    file: UploadFile,
    uid: Annotated[str, Depends(get_current_uid)],
) -> ExtractionResult:
    # TODO(BM): 변환 횟수(비용 동인) 한도 검사·증가 — users/{uid} (Firestore) 연동 시 추가.
    is_pdf = (file.content_type == "application/pdf") or (file.filename or "").lower().endswith(
        ".pdf"
    )
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="PDF 파일만 업로드할 수 있습니다.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="빈 파일입니다.")
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="파일이 너무 큽니다(최대 20MB).",
        )

    try:
        # PyMuPDF 는 동기 작업이라 이벤트 루프를 막지 않도록 스레드로 실행한다.
        result = await anyio.to_thread.run_sync(extract_from_pdf, data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF 를 처리할 수 없습니다. 손상되었거나 지원하지 않는 형식일 수 있습니다.",
        ) from exc

    return result
