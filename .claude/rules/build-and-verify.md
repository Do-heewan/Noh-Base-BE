# 빌드 & 검증 규칙

## "빌드"의 정의

이 프로젝트는 컴파일이 없는 Python이므로, **빌드 = 검증 게이트 통과**로 정의한다.
게이트는 `.claude/hooks/verify_build.py` 한 곳에 모여 있고, 순서대로:

| 단계 | 명령 | 무엇을 막나 |
| --- | --- | --- |
| format | `ruff format --check .` | 포맷 불일치 |
| lint | `ruff check .` | 미사용 import, 버그 패턴, import 정렬 등 |
| types | `mypy` (대상: `app`) | 타입 오류 |
| tests | `pytest` | 동작 회귀 |
| smoke | `import app.main` | 앱 자체가 기동 불가한 상태 |

## 실행 방법

```bash
# 전체 게이트
conda run -n Noh_Base_BE python .claude/hooks/verify_build.py

# 빠른 검사(pytest 제외) — 반복 수정 중 빠른 피드백
conda run -n Noh_Base_BE python .claude/hooks/verify_build.py --fast
```

종료 코드 0 = 통과, 1 = 실패. 실패 시 어떤 단계가 왜 실패했는지 상세 출력이 따라온다.

## 자가 수정 루프 (Stop 훅)

`.claude/hooks/stop_gate.py` 가 `.claude/settings.json` 의 `Stop` 훅으로 등록되어 있어,
턴을 마칠 때마다 자동 실행된다.

- **변경 감지**: `app/`·`tests/` 의 `.py` 들의 (경로·크기·mtime) 서명을 `.claude/.build_state.json` 에 저장한다.
  마지막 통과 이후 변경이 없으면 게이트를 건너뛰고 즉시 멈춤을 허용한다 → Q&A·문서 작업 턴은 느려지지 않는다.
- **실패 시**: `{"decision":"block"}` 으로 멈춤을 막고 실패 리포트를 반환한다.
  Claude 는 리포트를 읽고 **근본 원인을 코드로 수정**한 뒤 계속 진행한다.
- **루프 종료**: 게이트가 통과하면 멈춤 허용. 연속 6회(MAX_FAIL_STREAK) 실패하면 무한 루프 방지를 위해
  멈춤을 허용하되, 이때는 사용자에게 남은 실패를 보고한다.

## 수정 시 원칙

1. **우회 금지.** `# type: ignore` 남발, 테스트 skip/xfail 추가, 린트 규칙 비활성화로 통과시키지 않는다.
   진짜 원인을 고친다. (정당한 외부 라이브러리 스텁 부재 등은 예외이며 주석으로 이유를 남긴다.)
2. **포맷/안전 린트는 자동 정리 가능.** `ruff format .`, `ruff check --fix .` 로 기계적 항목을 먼저 정리하면
   남은 게 진짜 문제다.
3. **테스트가 깨지면** 코드가 틀렸는지 테스트 기대가 틀렸는지 판단한다. 기능 변경이 의도된 것이면 테스트도 함께 갱신한다.
4. **새 기능엔 테스트를 추가**한다. 라우터는 최소한 happy-path + 인증 실패 케이스를 가진다.

## 새 의존성 추가 시

`pyproject.toml` 의 `dependencies`(런타임) 또는 `[project.optional-dependencies].dev`(개발용)에 추가하고
`conda run -n Noh_Base_BE pip install -e ".[dev]"` 로 반영한다. 게이트가 import 실패로 잡아준다.
