"""디지털 PDF에서 (영어 표제어, 뜻) 쌍을 verbatim 추출한다.

전략 (기획서 4.2: 디지털 PDF 1순위):
  - PyMuPDF 로 텍스트 레이어를 그대로 읽는다.
  - 단어 좌표로 같은 줄(행)을 묶고, 행 안에서 term/meaning 을 분리한다.
  - 분리 시 '구분자'만 제거하고, term·meaning 문자열 자체는 손대지 않는다.
    (의학 접두/접미사의 하이픈 등 보존: '-itis', 'pre-', 'gastr/o')

텍스트 레이어가 없으면(스캔본 이미지 PDF) needs_ocr=True 로 표시하고 빈 결과를 반환한다.
OCR 폴백은 다음 단계에서 같은 인터페이스로 추가한다.
"""

from __future__ import annotations

import re

import fitz  # PyMuPDF

from app.models.extraction import ExtractedWord, ExtractionResult

# 한글 음절, 라틴 문자
_HANGUL = re.compile(r"[가-힣]")
_LATIN = re.compile(r"[A-Za-z]")
# 줄 맨 앞의 목록 마커(번호/불릿)만 제거 — 하이픈은 접사 보존을 위해 건드리지 않는다.
_LEADING_MARKER = re.compile(r"^(?:\d+[.)]|[•·▪◦*])\s+")
# 공백으로 둘러싸인 대시(구분자). 'x-ray' 같은 붙은 하이픈은 매칭되지 않는다.
_SPACED_DASH = re.compile(r"\s[—–-]\s")

# PyMuPDF "words" 튜플 인덱스: (x0, y0, x1, y1, word, block, line, word_no)
Word = tuple


def _mk(term: str, meaning: str) -> tuple[str, str | None] | None:
    """공백만 정리하고 verbatim 으로 (term, meaning) 구성. 영어 표제어가 없으면 None."""
    term = term.strip()
    meaning = meaning.strip()
    if not term or not _LATIN.search(term):
        return None
    return term, (meaning or None)


def parse_line(text: str) -> tuple[str, str | None] | None:
    """한 줄 문자열을 (term, meaning|None) 으로 분리. 분리 불가/영어 없음이면 None.

    우선순위: 콜론 > 공백 대시 > 라틴→한글 전환. 어느 것도 없으면 전체를 term 으로 본다.
    """
    text = _LEADING_MARKER.sub("", text.strip())
    if not _LATIN.search(text):
        return None

    if ":" in text:
        left, right = text.split(":", 1)
        return _mk(left, right)

    m = _SPACED_DASH.search(text)
    if m:
        return _mk(text[: m.start()], text[m.end() :])

    mh = _HANGUL.search(text)
    if mh and mh.start() > 0:
        return _mk(text[: mh.start()], text[mh.start() :])

    return _mk(text, "")


def _row_text(tokens: list[Word]) -> str:
    """행의 단어들을 x 순서대로 단일 공백으로 이어붙인다."""
    return " ".join(str(t[4]) for t in tokens)


def _largest_gap_split(tokens: list[Word]) -> int | None:
    """행 안에서 가장 큰 수평 간격(2열 경계)을 찾아 분리 인덱스를 반환.

    구분자도 스크립트 전환도 없는 영어-영어 2열(예: 토익 단어장) 대비.
    """
    if len(tokens) < 2:
        return None
    fontsize = max((t[3] - t[1]) for t in tokens)
    best_gap, best_idx = 0.0, None
    for i in range(1, len(tokens)):
        gap = tokens[i][0] - tokens[i - 1][2]
        if gap > best_gap:
            best_gap, best_idx = gap, i
    if best_idx is not None and best_gap > 1.5 * fontsize:
        return best_idx
    return None


def _group_rows(words: list[Word]) -> list[list[Word]]:
    """단어들을 수직 위치(행)로 묶는다. 2열 표도 같은 행으로 합쳐진다."""
    rows: list[dict] = []
    for w in sorted(words, key=lambda t: (round(t[1], 1), t[0])):
        cy = (w[1] + w[3]) / 2
        h = w[3] - w[1]
        for row in rows:
            if abs(cy - row["cy"]) <= 0.6 * max(h, row["h"]):
                row["words"].append(w)
                row["cy"] = (row["cy"] * row["n"] + cy) / (row["n"] + 1)
                row["n"] += 1
                row["h"] = max(row["h"], h)
                break
        else:
            rows.append({"cy": cy, "h": h, "n": 1, "words": [w]})

    rows.sort(key=lambda r: r["cy"])
    result: list[list[Word]] = []
    for r in rows:
        r["words"].sort(key=lambda t: t[0])
        result.append(r["words"])
    return result


def _parse_row(tokens: list[Word]) -> tuple[str, str | None] | None:
    """행 토큰에서 (term, meaning) 추출. 문자열 분리 우선, 실패 시 좌표 간격."""
    text = _row_text(tokens).strip()
    parsed = parse_line(text)
    if parsed is None:
        return None
    term, meaning = parsed
    if meaning is None:
        idx = _largest_gap_split(tokens)
        if idx is not None:
            left = _row_text(tokens[:idx])
            right = _row_text(tokens[idx:])
            return _mk(left, right)
    return term, meaning


def extract_from_pdf(pdf_bytes: bytes) -> ExtractionResult:
    """PDF 바이트에서 단어 항목을 추출한다."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page_count = doc.page_count
        total_text = 0
        words_out: list[ExtractedWord] = []
        for pno in range(page_count):
            page = doc[pno]
            total_text += len(page.get_text("text").strip())
            for tokens in _group_rows(list(page.get_text("words"))):
                parsed = _parse_row(tokens)
                if parsed is None:
                    continue
                term, meaning = parsed
                words_out.append(
                    ExtractedWord(
                        term=term,
                        meaning=meaning,
                        page=pno + 1,
                        raw_line=_row_text(tokens).strip(),
                    )
                )
    finally:
        doc.close()

    has_text_layer = total_text > 0
    # 텍스트가 0이거나 페이지당 평균이 빈약하면 OCR 폴백 대상으로 표시.
    needs_ocr = page_count > 0 and (total_text / page_count) < 5
    return ExtractionResult(
        words=words_out,
        page_count=page_count,
        has_text_layer=has_text_layer,
        needs_ocr=needs_ocr,
    )
