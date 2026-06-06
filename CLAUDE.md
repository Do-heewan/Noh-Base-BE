# Noh_Base_BE — 의학용어 단어장 학습 앱 백엔드

교수가 준 시험범위를 사진/PDF 한 장으로 단어장으로 만들어 외우게 해주는 앱의 **백엔드 API 서버**.
프론트엔드는 Flutter, 이 저장소는 백엔드만 담당한다.

## 기술 스택 (고정)

- **언어/런타임**: Python 3.11 — conda 가상환경 **`Noh_Base_BE`** 에서만 작업/실행한다.
- **프레임워크**: FastAPI + uvicorn
- **데이터/인증/스토리지**: Firebase — Auth(ID 토큰 검증), Firestore(데이터), Storage(업로드 파일)
  - FastAPI 는 `firebase-admin` SDK 로 토큰 검증·Firestore 읽기/쓰기를 한다. 자체 RDB/SQL 마이그레이션은 없다.
- **PDF/OCR**: 디지털 PDF 는 PyMuPDF 로 텍스트 레이어 직접 추출, 텍스트 레이어가 없으면 OCR 폴백.
- **검증 도구**: ruff(린트·포맷), mypy(타입), pytest(테스트).

## 항상 지키는 규칙

1. **모든 Python 실행은 conda 환경 `Noh_Base_BE` 에서.** 예: `conda run -n Noh_Base_BE python ...`, `conda run -n Noh_Base_BE pytest`. 시스템/base 파이썬을 쓰지 않는다.
2. **비밀은 커밋 금지.** `serviceAccountKey.json`, `.env` 는 `.gitignore` 에 있다. 설정은 `app/core/config.py` 의 `Settings` 를 통해서만 읽는다.
3. **의학용어 정확성이 최우선.** 자동 완성(DB 대조/LLM 폴백) 결과는 틀릴 수 있다는 전제로, 사용자 검수 단계를 항상 보존한다. 틀린 뜻은 사용자 영구 이탈을 부른다.
4. **비용 동인은 '변환 횟수'다.** 요금제/한도 로직은 단어 개수가 아니라 스캔·변환 횟수에 건다.
5. **새 기능은 핵심 루프(입력→추출→자동완성→검수→학습→지속)를 깨지 않는 선에서.** MVP 제외 항목(팀 공유, 손글씨 OCR, 게임 모드, 발음)은 구현하지 않는다.
6. **타입 힌트 필수.** 공개 함수·라우터·서비스는 인자/반환 타입을 명시한다 (mypy 통과 기준).

## 자동 빌드 & 자가 수정 워크플로우 (중요)

이 저장소에는 **개발이 끝나면 자동으로 빌드하고, 실패하면 스스로 고치고, 초록이 될 때까지 반복**하는 장치가 있다.

- **빌드의 단일 기준** = `.claude/hooks/verify_build.py` 의 게이트:
  `ruff format --check` → `ruff check` → `mypy` → `pytest` → 앱 import 스모크.
- **Stop 훅**(`.claude/hooks/stop_gate.py`, `.claude/settings.json` 에 등록)이 턴 종료 시마다 실행된다:
  - `app/`·`tests/` 의 `.py` 가 마지막 통과 이후 바뀌었을 때만 게이트를 돌린다(Q&A 턴은 즉시 통과).
  - 실패하면 멈춤을 막고 실패 리포트를 돌려주므로, **그 출력을 읽고 근본 원인을 고친 뒤 계속 진행**한다.
  - 연속 6회 실패하면 무한 루프 방지를 위해 멈춤을 허용한다(이때는 사용자에게 상황을 보고).
- **수동 실행**: `conda run -n Noh_Base_BE python .claude/hooks/verify_build.py` (빠른 검사는 `--fast`).
- 게이트를 우회하거나 테스트를 비활성화해 통과시키지 않는다. 실패는 코드로 해결한다.

자세한 내용: @.claude/rules/build-and-verify.md

## 상세 문서 (필요 시 읽기)

- 시스템 아키텍처/요청 흐름: @docs/architecture.md
- 기능 명세(MVP 범위·화면 흐름·BM): @docs/features.md
- API 표면(계획된 엔드포인트): @docs/api.md
- Firestore 데이터 모델: @.claude/rules/firestore-data-model.md
- Python 코드 컨벤션: @.claude/rules/python-style.md
