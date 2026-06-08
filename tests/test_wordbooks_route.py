"""단어장 저장·조회·삭제 라우터 테스트.

Firestore 는 인메모리 가짜 레포지토리로 대체하고, 토큰 검증은 dependency_overrides 로 우회한다.
서비스의 소유권 검증 로직은 실제로 실행된다(가짜는 레포지토리 레이어만 대체).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from app.core.firebase import get_current_uid
from app.main import app
from app.repositories.wordbooks import get_wordbook_repository
from fastapi.testclient import TestClient


class FakeWordbookRepository:
    """WordbookRepository 의 인메모리 대체. 같은 메서드 시그니처를 따른다."""

    def __init__(self) -> None:
        self._books: dict[str, dict[str, Any]] = {}
        self._words: dict[str, list[dict[str, Any]]] = {}
        self._seq = 0

    def _next_id(self) -> str:
        self._seq += 1
        return f"wb{self._seq}"

    def create(self, *, owner_uid: str, title: str, source_type: str, words: list[Any]) -> str:
        wid = self._next_id()
        self._books[wid] = {
            "id": wid,
            "owner_uid": owner_uid,
            "title": title,
            "source_type": source_type,
            "status": "review",
            "word_count": len(words),
            "created_at": datetime(2026, 6, 9, 12, 0, 0),
        }
        self._words[wid] = [
            {
                "id": f"{wid}-w{i}",
                "term": w.term,
                "meaning": w.meaning,
                "etymology": w.etymology,
                "source": w.source,
                "reviewed": False,
                "wrong_count": 0,
            }
            for i, w in enumerate(words)
        ]
        return wid

    def get(self, wordbook_id: str) -> dict[str, Any] | None:
        book = self._books.get(wordbook_id)
        return dict(book) if book is not None else None

    def list_for_owner(self, owner_uid: str) -> list[dict[str, Any]]:
        return [dict(b) for b in self._books.values() if b["owner_uid"] == owner_uid]

    def get_words(self, wordbook_id: str) -> list[dict[str, Any]]:
        return [dict(w) for w in self._words.get(wordbook_id, [])]

    def delete(self, wordbook_id: str) -> None:
        self._books.pop(wordbook_id, None)
        self._words.pop(wordbook_id, None)


@pytest.fixture
def fake_repo() -> FakeWordbookRepository:
    return FakeWordbookRepository()


@pytest.fixture
def client(fake_repo: FakeWordbookRepository) -> Iterator[TestClient]:
    """인증 우회 + 인메모리 레포지토리를 주입한 클라이언트(uid=user-1)."""
    app.dependency_overrides[get_current_uid] = lambda: "user-1"
    app.dependency_overrides[get_wordbook_repository] = lambda: fake_repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_uid, None)
        app.dependency_overrides.pop(get_wordbook_repository, None)


_PAYLOAD = {
    "title": "1주차 시험범위",
    "source_type": "pdf",
    "words": [
        {"term": "abdomen", "meaning": "복부", "source": "pdf"},
        {"term": "-itis", "meaning": None, "source": "pdf"},
    ],
}


def test_create_wordbook(client: TestClient) -> None:
    resp = client.post("/wordbooks", json=_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "1주차 시험범위"
    assert body["status"] == "review"
    assert body["word_count"] == 2
    assert body["owner_uid"] == "user-1"
    assert "id" in body


def test_list_only_returns_own(client: TestClient, fake_repo: FakeWordbookRepository) -> None:
    client.post("/wordbooks", json=_PAYLOAD)
    # 다른 사용자의 단어장은 목록에 섞이지 않아야 한다.
    fake_repo.create(owner_uid="other", title="남의 것", source_type="pdf", words=[])

    resp = client.get("/wordbooks")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["title"] == "1주차 시험범위"


def test_get_detail_returns_words(client: TestClient) -> None:
    wid = client.post("/wordbooks", json=_PAYLOAD).json()["id"]

    resp = client.get(f"/wordbooks/{wid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["word_count"] == 2
    terms = {w["term"] for w in body["words"]}
    assert terms == {"abdomen", "-itis"}
    # verbatim 보존: 빈 뜻은 None 으로 내려간다.
    itis = next(w for w in body["words"] if w["term"] == "-itis")
    assert itis["meaning"] is None


def test_get_others_wordbook_is_404(client: TestClient, fake_repo: FakeWordbookRepository) -> None:
    other_id = fake_repo.create(owner_uid="other", title="남의 것", source_type="pdf", words=[])
    resp = client.get(f"/wordbooks/{other_id}")
    assert resp.status_code == 404


def test_delete_wordbook(client: TestClient) -> None:
    wid = client.post("/wordbooks", json=_PAYLOAD).json()["id"]

    assert client.delete(f"/wordbooks/{wid}").status_code == 204
    # 삭제 후 조회는 404.
    assert client.get(f"/wordbooks/{wid}").status_code == 404


def test_delete_others_wordbook_is_404(
    client: TestClient, fake_repo: FakeWordbookRepository
) -> None:
    other_id = fake_repo.create(owner_uid="other", title="남의 것", source_type="pdf", words=[])
    assert client.delete(f"/wordbooks/{other_id}").status_code == 404
    # 남의 단어장은 그대로 남아 있어야 한다.
    assert fake_repo.get(other_id) is not None


def test_wordbooks_require_auth() -> None:
    resp = TestClient(app).get("/wordbooks")
    assert resp.status_code == 401
