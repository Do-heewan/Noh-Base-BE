# Firestore 데이터 모델

자체 RDB/SQL 스키마·마이그레이션은 없다. 모든 영속 데이터는 Firestore(NoSQL) 컬렉션에 둔다.
문서 형태는 아래를 기준으로 하되, 기능 개발 중 필드를 추가할 땐 이 문서를 함께 갱신한다.

## 컬렉션

### `users/{uid}`
Firebase Auth 의 uid 를 문서 ID 로 사용한다.
```
{
  "email": str,
  "admission_type": "current" | "transfer" | "mature",   # 현역/편입/만학 — BM 가설 검증용
  "plan": "free" | "pro",
  "conversions_used": int,            # 이번 주기 변환 횟수 (비용 동인)
  "conversions_reset_at": timestamp,  # 한도 리셋 시점
  "streak_count": int,
  "last_studied_on": date,
  "created_at": timestamp
}
```

### `wordbooks/{wordbook_id}`
```
{
  "owner_uid": str,          # users/{uid} 참조
  "title": str,
  "source_type": "pdf" | "camera" | "image_pdf",
  "status": "extracting" | "review" | "ready",   # 검수 전/후 상태
  "word_count": int,
  "created_at": timestamp
}
```

### `wordbooks/{wordbook_id}/words/{word_id}` (서브컬렉션)
```
{
  "term": str,             # 영어 의학용어 (표제어)
  "meaning": str,          # 뜻
  "etymology": str | null, # 어원
  "source": "db" | "llm" | "user",  # 자동완성 출처 (검수 데이터 적립용)
  "reviewed": bool,        # 사용자 검수 완료 여부
  "wrong_count": int       # 오답 누적
}
```

### `medical_terms/{normalized_term}`
자체 의학용어 DB(닫힌 어휘, 재사용 자산). 문서 ID = 소문자·trim 한 표제어(정규화 키)로 O(1) 조회.
```
{
  "term": str,             # 원형 표제어
  "meaning": str,
  "etymology": str | null,
  "verified": bool         # 사용자 검수로 적립된 항목인지
}
```
LLM 폴백 결과는 사용자 검수를 거친 뒤 이 컬렉션에 `verified:false`(또는 검토 후 true)로 적립해 점진 보강한다.

### `quiz_results/{result_id}`
```
{
  "uid": str,
  "wordbook_id": str,
  "score": float,          # 정답률
  "wrong_word_ids": [str],
  "created_at": timestamp
}
```

## 규칙

- 문서 ID 는 의미 있는 키를 쓸 수 있으면 쓴다(`users`=uid, `medical_terms`=정규화 표제어). 그 외는 자동 ID.
- 사용자 소유 데이터는 항상 `owner_uid`/`uid` 로 소유권을 검증한 뒤 반환한다 (다른 사용자 데이터 노출 금지).
- 비용 동인은 변환 횟수다. 변환(스캔/추출) 시작 시 `users.conversions_used` 를 증가시키고 Free 한도를 검사한다.
- 타임스탬프는 Firestore 서버 타임스탬프(`SERVER_TIMESTAMP`)를 사용한다.
- 접근은 `app/repositories/` 의 레포지토리를 통해서만. 라우터/서비스에서 컬렉션 경로를 직접 문자열로 다루지 않는다.
