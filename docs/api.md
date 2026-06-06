# API 표면 (계획)

> 현재 구현된 것은 `GET /health` 뿐이다. 아래는 핵심 루프를 따라 단계적으로 추가할 **계획된** 엔드포인트다.
> 실제 구현 시 이 문서를 함께 갱신한다. 모든 보호된 엔드포인트는 `Authorization: Bearer <Firebase ID token>` 필요.

## 인증 / 사용자

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/users/me` | 첫 로그인 시 사용자 문서 생성 (입학 유형 수집: 현역/편입/만학) |
| GET | `/users/me` | 내 프로필·플랜·잔여 변환 횟수·스트릭 조회 |

## 단어장 생성 (핵심 루프)

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/wordbooks/extract` | PDF/이미지 업로드 → 추출 + DB 매칭 → `status=review` 단어장 생성. Free 한도 검사·변환 횟수 증가 |
| GET | `/wordbooks` | 내 단어장 목록 (홈 화면) |
| GET | `/wordbooks/{id}` | 단어장 + 단어 목록 (검수 화면) |
| PATCH | `/wordbooks/{id}/words/{word_id}` | 단어 뜻·어원 수정 (검수) |
| POST | `/wordbooks/{id}/confirm` | 검수 완료 → `status=ready`, 검수 결과 `medical_terms` 적립 |
| DELETE | `/wordbooks/{id}` | 단어장 삭제 |

## 학습

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/wordbooks/{id}/quiz` | 객관식·주관식 랜덤 문제 세트 생성 |
| POST | `/wordbooks/{id}/quiz/submit` | 답안 채점 → 정답률, 오답 누적, 스트릭 갱신 |
| GET | `/wordbooks/{id}/wrong` | 오답만 다시 풀기용 단어 조회 |
| GET | `/study/calendar` | 학습 캘린더·스트릭 |

## 규칙

- 응답 본문은 Pydantic 모델로 직렬화. 오류는 `HTTPException` + 한국어 `detail`.
- 소유권: `{id}` 리소스는 `owner_uid == 현재 uid` 검증 후에만 반환/수정.
- 변환(`/extract`)은 비용 동인 — Free 한도 초과 시 `402`/`403` 으로 Pro 유도.
- 페이지네이션이 필요한 목록은 커서 기반(Firestore `start_after`).
