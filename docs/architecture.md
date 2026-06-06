# 시스템 아키텍처

## 구성요소

```
┌─────────────┐        ┌──────────────────────────┐        ┌──────────────────┐
│  Flutter 앱  │        │   FastAPI (이 저장소)      │        │     Firebase      │
│  (FE)       │        │                          │        │                  │
│             │ HTTPS  │  - Firebase ID 토큰 검증   │  Admin │  - Auth          │
│  Firebase   ├───────►│  - PDF 추출 / OCR 폴백     ├───────►│  - Firestore     │
│  Auth 로그인 │ Bearer │  - 의학용어 DB 대조        │  SDK   │  - Storage       │
│             │ 토큰    │  - LLM 폴백              │        │                  │
└─────────────┘        │  - 퀴즈 생성 / 채점        │        └──────────────────┘
                       └────────────┬─────────────┘
                                    │ 미수록 단어
                                    ▼
                            ┌──────────────┐
                            │   LLM API    │
                            └──────────────┘
```

- **인증**: Flutter 가 Firebase Auth 로 직접 로그인 → ID 토큰을 `Authorization: Bearer` 로 전송.
  FastAPI 는 `firebase-admin` 으로 토큰을 검증해 `uid` 를 얻는다 (`app/core/firebase.py: get_current_uid`).
- **데이터**: 모든 영속 데이터는 Firestore. 스키마는 @.claude/rules/firestore-data-model.md.
- **파일**: 업로드 PDF/이미지는 Firebase Storage. 처리 후 원본 보관은 정책에 따름.

## 핵심 루프의 요청 흐름

1. `POST /wordbooks/extract` — 파일(PDF/이미지) 업로드.
   - Free 한도 검사 → `users.conversions_used` 증가.
   - PDF: 텍스트 레이어 있으면 PyMuPDF 직접 추출, 없으면 OCR. 카메라 이미지: OCR.
   - 영어 의학용어 토큰 추출 → 정규화.
2. **자동 완성** — 각 단어를 `medical_terms/{normalized}` 로 조회. 미스는 LLM 폴백.
   - 결과로 `wordbook(status=review)` + `words` 서브컬렉션 생성.
3. `GET /wordbooks/{id}` / `PATCH .../words/{wid}` — 사용자 검수·수정.
4. `POST /wordbooks/{id}/confirm` — 검수 완료 → `status=ready`, 검수된 단어를 `medical_terms` 에 적립.
5. `POST /wordbooks/{id}/quiz` — 객관식·주관식 문제 생성. `POST .../quiz/submit` — 채점·오답 누적·스트릭 갱신.

## 레이어

`api/routes`(얇게) → `services`(로직) → `repositories`(Firestore 접근). 횡단 관심사(설정·인증·Firebase 핸들)는 `core`.
자세한 코드 규칙: @.claude/rules/python-style.md

## 처리 분기 (PDF의 함정)

교수 배포 PDF 는 스캔본(이미지 PDF)인 경우가 많다. 추출기는 **텍스트 레이어 유무로 분기**하고,
OCR 엔진 하나로 카메라 입력 + 이미지 PDF 를 함께 커버한다.

## 운영 메모

- 비밀(서비스 계정 키, LLM 키)은 환경변수/`.env`. 운영은 `GOOGLE_APPLICATION_CREDENTIALS` 또는 워크로드 ID 권장.
- 비용 동인은 변환 횟수. OCR/LLM 호출 수를 모니터링 지표로 삼는다.
