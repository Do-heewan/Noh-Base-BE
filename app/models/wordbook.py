"""단어장(wordbook) 요청/응답 스키마.

Firestore 데이터 모델(.claude/rules/firestore-data-model.md)의 `wordbooks` 문서와
`words` 서브컬렉션을 그대로 반영한다. term/meaning 은 추출 원문(verbatim)을 보존한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# 단어 뜻의 출처. "pdf" = 업로드 문서에 적혀 있던 뜻(verbatim),
# "db"/"llm" = 자동완성, "user" = 사용자가 검수하며 입력/수정.
WordSource = Literal["pdf", "db", "llm", "user"]
# 입력 매체.
SourceType = Literal["pdf", "camera", "image_pdf"]
# 검수 전/후 상태.
WordbookStatus = Literal["extracting", "review", "ready"]


class WordCreate(BaseModel):
    """단어장 생성 시 저장할 한 단어 항목."""

    term: str = Field(..., min_length=1, description="영어(라틴) 표제어 — 원문 verbatim")
    meaning: str | None = Field(None, description="뜻 — 없으면 이후 자동완성(DB/LLM) 대상")
    etymology: str | None = Field(None, description="어원")
    source: WordSource = Field("pdf", description="뜻의 출처")


class WordbookCreateRequest(BaseModel):
    """단어장 생성 요청. 추출/검수 결과를 받아 review 상태로 저장한다."""

    title: str = Field(..., min_length=1, max_length=200)
    source_type: SourceType = Field("pdf")
    words: list[WordCreate] = Field(default_factory=list)


class WordRead(BaseModel):
    """words 서브컬렉션 한 문서의 응답 표현."""

    id: str
    term: str
    meaning: str | None = None
    etymology: str | None = None
    source: WordSource = "pdf"
    reviewed: bool = False
    wrong_count: int = 0


class WordbookSummary(BaseModel):
    """단어장 목록/생성 응답 (단어 미포함)."""

    id: str
    owner_uid: str
    title: str
    source_type: SourceType
    status: WordbookStatus
    word_count: int
    created_at: datetime | None = None


class WordbookDetail(WordbookSummary):
    """단어장 + 단어 목록 (검수 화면)."""

    words: list[WordRead] = Field(default_factory=list)
