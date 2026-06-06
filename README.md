# Noh_Base_BE

의학용어 단어장 학습 앱의 백엔드 API 서버 (FastAPI + Firebase). 프론트엔드는 Flutter.

> 교수가 준 시험범위를 사진/PDF 한 장으로 단어장으로 만들어 외우게 해주는 앱.
> 기획 배경·기능은 [docs/features.md](docs/features.md), 아키텍처는 [docs/architecture.md](docs/architecture.md) 참고.

## 빠른 시작

```bash
# 1. conda 가상환경 생성 (Python 3.11, 이름은 프로젝트와 동일)
conda create -y -n Noh_Base_BE python=3.11

# 2. 의존성 설치
conda run -n Noh_Base_BE pip install -e ".[dev]"

# 3. 환경변수 준비 (Firebase 서비스 계정 키 등)
cp .env.example .env   # 값 채우기, serviceAccountKey.json 배치

# 4. 개발 서버 실행
conda run -n Noh_Base_BE uvicorn app.main:app --reload
# http://127.0.0.1:8000/health , 문서: /docs
```

## 빌드 / 검증

"빌드" = 검증 게이트 통과. 한 줄로 실행:

```bash
conda run -n Noh_Base_BE python .claude/hooks/verify_build.py        # 전체
conda run -n Noh_Base_BE python .claude/hooks/verify_build.py --fast # pytest 제외
```

게이트: `ruff format --check` → `ruff check` → `mypy` → `pytest` → 앱 import 스모크.

## Claude Code 자동화

이 저장소는 Claude Code 로 자율 개발하도록 구성돼 있다.

- **CLAUDE.md** — 항상 적용되는 규칙. `.claude/rules/`, `docs/` 를 @import.
- **자동 빌드·자가 수정 루프** — `.claude/settings.json` 의 `Stop` 훅(`.claude/hooks/stop_gate.py`)이
  코드 변경 후 턴 종료 시 빌드 게이트를 돌리고, 실패하면 초록이 될 때까지 스스로 고치게 한다.
  자세히: [.claude/rules/build-and-verify.md](.claude/rules/build-and-verify.md)
- **build-fixer** 서브에이전트 — 빌드 실패를 명시적으로 위임해 고칠 때 사용.

## 구조

```
app/        FastAPI 앱 (core/ api/routes/ services/ repositories/ models/)
tests/      pytest
docs/       아키텍처·기능·API 문서 (CLAUDE.md 가 import)
.claude/    rules/ agents/ hooks/ settings.json
```
