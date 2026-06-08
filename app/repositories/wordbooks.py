"""wordbooks 컬렉션 + words 서브컬렉션 Firestore 접근.

문서 형태는 .claude/rules/firestore-data-model.md 기준. 소유권 검증·HTTP 오류 변환은
이 레이어가 아니라 서비스(app/services/wordbooks.py)에서 한다. 여기서는 순수 CRUD 만 한다.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from firebase_admin import firestore

from app.core.firebase import get_firestore
from app.models.wordbook import WordCreate

_COLLECTION = "wordbooks"
_WORDS = "words"


class WordbookRepository:
    """단어장 문서와 그 단어 서브컬렉션에 대한 Firestore 접근."""

    def __init__(self, db: firestore.Client) -> None:
        self._db = db

    def _doc(self, wordbook_id: str) -> Any:
        return self._db.collection(_COLLECTION).document(wordbook_id)

    def create(
        self,
        *,
        owner_uid: str,
        title: str,
        source_type: str,
        words: list[WordCreate],
    ) -> str:
        """단어장 문서 + 단어 서브컬렉션을 원자적(batch)으로 생성하고 새 id 를 반환."""
        doc_ref = self._db.collection(_COLLECTION).document()
        batch = self._db.batch()
        batch.set(
            doc_ref,
            {
                "owner_uid": owner_uid,
                "title": title,
                "source_type": source_type,
                "status": "review",
                "word_count": len(words),
                "created_at": firestore.SERVER_TIMESTAMP,
            },
        )
        words_col = doc_ref.collection(_WORDS)
        for w in words:
            batch.set(
                words_col.document(),
                {
                    "term": w.term,
                    "meaning": w.meaning,
                    "etymology": w.etymology,
                    "source": w.source,
                    "reviewed": False,
                    "wrong_count": 0,
                },
            )
        batch.commit()
        return str(doc_ref.id)

    def get(self, wordbook_id: str) -> dict[str, Any] | None:
        """단어장 문서(단어 미포함). 없으면 None."""
        snap = self._doc(wordbook_id).get()
        if not snap.exists:
            return None
        data = dict(snap.to_dict() or {})
        data["id"] = snap.id
        return data

    def list_for_owner(self, owner_uid: str) -> list[dict[str, Any]]:
        """소유자의 단어장 목록(최신순). 단어는 포함하지 않는다."""
        query = (
            self._db.collection(_COLLECTION)
            .where("owner_uid", "==", owner_uid)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )
        out: list[dict[str, Any]] = []
        for snap in query.stream():
            data = dict(snap.to_dict() or {})
            data["id"] = snap.id
            out.append(data)
        return out

    def get_words(self, wordbook_id: str) -> list[dict[str, Any]]:
        """단어장의 단어 서브컬렉션 전체."""
        out: list[dict[str, Any]] = []
        for snap in self._doc(wordbook_id).collection(_WORDS).stream():
            data = dict(snap.to_dict() or {})
            data["id"] = snap.id
            out.append(data)
        return out

    def delete(self, wordbook_id: str) -> None:
        """단어 서브컬렉션을 먼저 비우고 단어장 문서를 삭제한다."""
        doc_ref = self._doc(wordbook_id)
        for snap in doc_ref.collection(_WORDS).stream():
            snap.reference.delete()
        doc_ref.delete()


def get_wordbook_repository(
    db: Annotated[firestore.Client, Depends(get_firestore)],
) -> WordbookRepository:
    """라우터/서비스에서 Depends 로 주입하는 레포지토리 팩토리."""
    return WordbookRepository(db)
