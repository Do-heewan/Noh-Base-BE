# Python / FastAPI 코드 컨벤션

## 레이아웃

```
app/
  main.py              # create_app(), 라우터 include
  core/                # 설정, Firebase, 공통 의존성 (config.py, firebase.py)
  api/routes/          # 라우터 (도메인별 파일: wordbooks.py, extraction.py, quiz.py ...)
  services/            # 비즈니스 로직 (추출/매칭/퀴즈 생성 등) — 라우터에서 호출
  models/              # Pydantic 스키마 (요청/응답/도메인)
  repositories/        # Firestore 접근 캡슐화 (컬렉션별)
tests/                 # app 구조를 거울처럼 따라감
```

라우터는 얇게 유지한다: 입력 검증 → 서비스 호출 → 응답 변환. 로직은 `services/` 에.
Firestore 직접 접근은 `repositories/` 에 가두고, 서비스는 레포지토리를 통해서만 데이터에 접근한다.

## 규칙

- **타입 힌트 필수.** 공개 함수/메서드는 인자·반환 타입을 명시 (mypy 통과).
- **async 우선.** 라우터·I/O 함수는 `async def`. firebase-admin 동기 호출은 필요 시 `anyio.to_thread` 로 감싼다.
- **Pydantic v2.** 모델은 `BaseModel`, 설정은 `BaseSettings`. `model_config` 사용.
- **의존성 주입.** 설정·Firestore·현재 사용자(uid)는 `Depends` 로 주입 (`app/core/firebase.py` 참고).
- **예외.** 사용자 대상 오류는 `HTTPException` + 적절한 상태코드 + 한국어 `detail`. 내부 오류는 로깅하고 500으로.
- **네이밍.** 모듈/함수/변수 `snake_case`, 클래스 `PascalCase`. 컬렉션·필드명은 데이터 모델 문서 기준.
- **주변 코드 스타일을 따른다.** 한국어 주석/docstring 을 사용하되, 식별자는 영어.
- **줄 길이 100자**, 정렬·포맷은 ruff 가 강제한다 — 직접 맞추려 애쓰지 말고 `ruff format .` 을 돌린다.

## 안티패턴

- 라우터에 Firestore 쿼리를 직접 박지 않는다 (레포지토리로).
- 전역 가변 상태 금지. 설정/클라이언트는 `lru_cache` 싱글턴으로.
- 광범위 `except Exception` 은 경계(토큰 검증, 외부 호출)에서만, 반드시 재발생 또는 로깅.
