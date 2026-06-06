"""Firebase Admin 초기화 및 인증 의존성.

Flutter 앱이 Firebase Auth 로 로그인하고 ID 토큰을 보내면,
여기서 토큰을 검증해 uid 를 추출한다. Firestore/Storage 핸들도 제공한다.
"""

from __future__ import annotations

import functools
from typing import Annotated, Any

import firebase_admin
from fastapi import Depends, Header, HTTPException, status
from firebase_admin import auth, credentials, firestore

from app.core.config import Settings, get_settings


@functools.lru_cache
def _init_app() -> firebase_admin.App:
    settings = get_settings()
    cred = credentials.Certificate(settings.firebase_credentials_path)
    options: dict[str, Any] = {}
    if settings.firebase_storage_bucket:
        options["storageBucket"] = settings.firebase_storage_bucket
    return firebase_admin.initialize_app(cred, options)


def get_firestore() -> firestore.Client:
    """Firestore 클라이언트. 라우터에서 Depends 로 주입한다."""
    _init_app()
    return firestore.client()


async def get_current_uid(
    authorization: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
) -> str:
    """Authorization: Bearer <Firebase ID token> 을 검증해 uid 반환."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer 토큰이 필요합니다.",
        )
    token = authorization.split(" ", 1)[1].strip()
    _init_app()
    try:
        decoded = auth.verify_id_token(token)
    except Exception as exc:  # firebase_admin 의 다양한 예외를 일괄 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        ) from exc
    return str(decoded["uid"])
