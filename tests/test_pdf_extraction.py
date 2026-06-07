"""PDF 추출 서비스 테스트.

- 한글 뜻 파싱은 폰트 의존을 피해 parse_line(순수 문자열)로 단위 검증.
- 추출 전 과정은 ASCII 로 실제 PDF 를 생성해 검증(verbatim 하이픈 보존 포함).
"""

from __future__ import annotations

import fitz
import pytest
from app.services.pdf_extraction import extract_from_pdf, parse_line


def _make_pdf(lines: list[str], fontsize: int = 12) -> bytes:
    """각 문자열을 한 줄로 그린 단순 PDF 바이트 생성."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for line in lines:
        page.insert_text((72, y), line, fontsize=fontsize)
        y += 2.2 * fontsize
    data = doc.tobytes()
    doc.close()
    return data


def _two_column_pdf(pairs: list[tuple[str, str]], fontsize: int = 12) -> bytes:
    """term 은 좌측(x=72), meaning 은 우측(x=320)에 배치한 2열 PDF (구분자 없음)."""
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for term, meaning in pairs:
        page.insert_text((72, y), term, fontsize=fontsize)
        page.insert_text((320, y), meaning, fontsize=fontsize)
        y += 2.2 * fontsize
    data = doc.tobytes()
    doc.close()
    return data


# --------------------------- parse_line 단위 ---------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("abdomen: 복부", ("abdomen", "복부")),
        ("cardio 심장", ("cardio", "심장")),  # 라틴→한글 전환
        ("blood pressure 혈압", ("blood pressure", "혈압")),  # 다중 단어 term 보존
        ("abdomen — belly", ("abdomen", "belly")),  # 공백 em-dash 구분자
        ("abdomen - belly", ("abdomen", "belly")),  # 공백 하이픈 구분자
        ("-itis: inflammation", ("-itis", "inflammation")),  # 접미사 하이픈 보존
        ("pre-: 이전", ("pre-", "이전")),  # 접두사 하이픈 보존
        ("x-ray 엑스레이", ("x-ray", "엑스레이")),  # term 내부 하이픈은 분리하지 않음
        ("1. abdomen 복부", ("abdomen", "복부")),  # 줄 앞 번호 마커 제거
        ("• cardio 심장", ("cardio", "심장")),  # 불릿 마커 제거
        ("abdomen", ("abdomen", None)),  # 뜻 없음
    ],
)
def test_parse_line(line: str, expected: tuple[str, str | None]) -> None:
    assert parse_line(line) == expected


def test_parse_line_no_latin_is_skipped() -> None:
    assert parse_line("복부") is None
    assert parse_line("123") is None


# --------------------------- 실제 PDF 추출 ---------------------------


def test_extract_english_pairs_verbatim() -> None:
    pdf = _make_pdf(["abdomen: belly", "cardio: heart"])
    result = extract_from_pdf(pdf)

    assert result.has_text_layer is True
    assert result.needs_ocr is False
    assert result.page_count == 1
    terms = {w.term: w.meaning for w in result.words}
    assert terms["abdomen"] == "belly"
    assert terms["cardio"] == "heart"
    assert all(w.page == 1 for w in result.words)


def test_extract_preserves_affix_hyphen() -> None:
    """교수 자료 verbatim 핵심: '-itis' 의 하이픈이 보존되어야 한다."""
    pdf = _make_pdf(["-itis: inflammation"])
    result = extract_from_pdf(pdf)
    terms = [w.term for w in result.words]
    assert "-itis" in terms


def test_extract_term_without_meaning() -> None:
    pdf = _make_pdf(["abdomen"])
    result = extract_from_pdf(pdf)
    assert len(result.words) == 1
    assert result.words[0].term == "abdomen"
    assert result.words[0].meaning is None


def test_extract_two_column_layout() -> None:
    pdf = _two_column_pdf([("abdomen", "belly"), ("thorax", "chest")])
    result = extract_from_pdf(pdf)
    terms = {w.term: w.meaning for w in result.words}
    assert terms.get("abdomen") == "belly"
    assert terms.get("thorax") == "chest"


def test_image_pdf_flags_needs_ocr() -> None:
    """텍스트 레이어 없는(빈) PDF 는 OCR 폴백 대상으로 표시."""
    doc = fitz.open()
    doc.new_page()  # 텍스트 없는 빈 페이지
    data = doc.tobytes()
    doc.close()

    result = extract_from_pdf(data)
    assert result.has_text_layer is False
    assert result.needs_ocr is True
    assert result.words == []
