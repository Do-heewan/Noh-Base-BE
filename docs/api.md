# API 표면 (계획)

> 구현 상태: `GET /health`, `POST /extract/pdf`(디지털 PDF 추출), 단어장 저장·조회·삭제(아래 ✅).
> 나머지는 핵심 루프를 따라 단계적으로 추가할 **계획된** 엔드포인트다.
> 실제 구현 시 이 문서를 함께 갱신한다. 모든 보호된 엔드포인트는 `Authorization: Bearer <Firebase ID token>` 필요.

## 인증 / 사용자

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/users/me` | 첫 로그인 시 사용자 문서 생성 (입학 유형 수집: 현역/편입/만학) |
| GET | `/users/me` | 내 프로필·플랜·잔여 변환 횟수·스트릭 조회 |

## 단어장 생성 (핵심 루프)

| 메서드 | 경로 | 상태 | 설명 |
| --- | --- | --- | --- |
| POST | `/extract/pdf` | ✅ | 디지털 PDF 업로드 → (영단어, 뜻) verbatim 추출 결과 반환 (저장 안 함) |
| POST | `/wordbooks` | ✅ | 추출/검수 결과를 받아 `status=review` 단어장으로 저장 |
| GET | `/wordbooks` | ✅ | 내 단어장 목록 (홈 화면, 최신순) |
| GET | `/wordbooks/{id}` | ✅ | 단어장 + 단어 목록 (검수 화면). 소유자 외 404 |
| DELETE | `/wordbooks/{id}` | ✅ | 단어장 삭제. 소유자 외 404 |
| PATCH | `/wordbooks/{id}/words/{word_id}` | 계획 | 단어 뜻·어원 수정 (검수) |
| POST | `/wordbooks/{id}/confirm` | 계획 | 검수 완료 → `status=ready`, 검수 결과 `medical_terms` 적립 |
| POST | `/wordbooks/extract` | 계획 | (추출+저장 단축 경로) Free 한도 검사·변환 횟수 증가 포함 |

> 현재는 추출(`POST /extract/pdf`)과 저장(`POST /wordbooks`)을 분리했다. FE 는 추출 결과를 검수 화면에서
> 보정한 뒤 `POST /wordbooks` 로 저장한다. 변환 한도(비용 동인) 검사는 추출/저장 시점에 추후 추가한다.

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
