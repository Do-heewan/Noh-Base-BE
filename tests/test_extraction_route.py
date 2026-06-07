"""POST /extract/pdf 라우터 테스트.

Firebase 토큰 검증은 dependency_overrides 로 우회한다(실제 Firebase 자격증명 불필요).
"""

from __future__ import annotations

from collections.abc import Iterator

import fitz
import pytest
from app.core.firebase import get_current_uid
from app.main import app
from fastapi.testclient import TestClient


def _make_pdf(lines: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72.0
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 26
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
    """인증을 우회한 클라이언트."""
    app.dependency_overrides[get_current_uid] = lambda: "test-uid"
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_uid, None)


def test_extract_pdf_returns_words(auth_client: TestClient) -> None:
    pdf = _make_pdf(["abdomen: belly"])
    resp = auth_client.post(
        "/extract/pdf",
        files={"file": ("range.pdf", pdf, "application/pdf")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_text_layer"] is True
    assert any(w["term"] == "abdomen" and w["meaning"] == "belly" for w in body["words"])


def test_extract_rejects_non_pdf(auth_client: TestClient) -> None:
    resp = auth_client.post(
        "/extract/pdf",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_extract_requires_auth() -> None:
    """오버라이드 없이(토큰 없음) 호출하면 401."""
    pdf = _make_pdf(["abdomen: belly"])
    client = TestClient(app)
    resp = client.post(
        "/extract/pdf",
        files={"file": ("range.pdf", pdf, "application/pdf")},
    )
    assert resp.status_code == 401
