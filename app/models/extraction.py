"""PDF 추출 결과 스키마.

핵심 원칙: term/meaning 문자열은 PDF에 적힌 그대로(verbatim) 보존한다.
철자·표기를 정규화/교정하지 않는다 (교수 자료와 토시 하나 안 틀리게 일치해야 함).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExtractedWord(BaseModel):
    """PDF에서 추출한 한 단어 항목."""

    term: str = Field(..., description="영어(라틴) 표제어 — PDF 원문 그대로")
    meaning: str | None = Field(
        None, description="뜻 — PDF에 있으면 원문 그대로, 없으면 None(이후 DB/LLM 자동완성 대상)"
    )
    page: int = Field(..., ge=1, description="원본 PDF 페이지 번호 (1-based)")
    raw_line: str = Field(..., description="추출 근거가 된 원본 행 텍스트 (검수·감사용)")
    source: Literal["pdf"] = "pdf"


class ExtractionResult(BaseModel):
    """단어장 추출 결과."""

    words: list[ExtractedWord] = Field(default_factory=list)
    page_count: int = Field(..., ge=0)
    has_text_layer: bool = Field(..., description="디지털 PDF(텍스트 레이어) 여부")
    needs_ocr: bool = Field(
        ..., description="텍스트 레이어가 없거나 빈약해 OCR 폴백이 필요한지 (OCR은 다음 단계)"
    )
