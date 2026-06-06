#!/usr/bin/env python
"""Stop 훅 — '빌드가 초록이 되기 전엔 멈추지 않는다' 자동 수정 루프.

Claude 가 턴을 끝내려 할 때마다 호출된다. 동작:
  1. 마지막 통과 이후 Python 소스(app/, tests/)가 바뀌었는지 검사.
     - 안 바뀌었으면(예: 단순 Q&A 턴) 게이트를 돌리지 않고 즉시 통과시킨다.
  2. 바뀌었으면 빌드 게이트(verify_build.run_gate)를 실행한다.
     - 통과: 서명을 저장하고 정상 종료(멈춤 허용).
     - 실패: {"decision":"block"} 으로 실패 리포트를 돌려줘 Claude 가 고치게 한다.
  3. 무한 루프 방지: 연속 실패가 MAX_FAIL_STREAK 를 넘으면 경고와 함께 멈춤을 허용한다.

Stop 훅 입력(JSON, stdin): stop_hook_active 등.
출력(JSON, stdout): {"decision":"block","reason":...} 또는 빈/허용.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = HOOK_DIR.parents[1]
STATE_FILE = HOOK_DIR.parent / ".build_state.json"
MAX_FAIL_STREAK = 6
SRC_DIRS = ("app", "tests")

sys.path.insert(0, str(HOOK_DIR))
from verify_build import run_gate  # noqa: E402


def _source_signature() -> str:
    """app/, tests/ 의 모든 *.py 에 대한 (경로,크기,mtime) 해시."""
    h = hashlib.sha256()
    files: list[Path] = []
    for d in SRC_DIRS:
        files.extend((PROJECT_ROOT / d).rglob("*.py"))
    for f in sorted(files):
        try:
            st = f.stat()
        except OSError:
            continue
        h.update(str(f.relative_to(PROJECT_ROOT)).encode())
        h.update(str(st.st_size).encode())
        h.update(str(st.st_mtime_ns).encode())
    return h.hexdigest()


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last_pass_signature": "", "fail_streak": 0}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def _allow() -> None:
    """멈춤 허용 (추가 출력 없음)."""
    raise SystemExit(0)


def _block(reason: str) -> None:
    """멈춤 차단 — reason 이 Claude 에게 전달되어 작업을 계속하게 한다."""
    print(json.dumps({"decision": "block", "reason": reason}))
    raise SystemExit(0)


def main() -> None:
    # Stop 훅 입력(JSON)을 소비한다. 현재 stop_hook_active 대신 자체 fail_streak 로
    # 루프를 제어하므로 내용은 사용하지 않는다.
    try:
        json.load(sys.stdin)
    except (ValueError, OSError):
        pass

    sig = _source_signature()
    state = _load_state()

    # 변경 없음 → 마지막으로 초록이었던 상태 그대로. 게이트 생략하고 통과.
    if sig and sig == state.get("last_pass_signature"):
        if state.get("fail_streak"):  # 알려진 정상 상태이므로 실패 카운터 리셋
            _save_state({"last_pass_signature": sig, "fail_streak": 0})
        _allow()

    ok, report = run_gate()

    if ok:
        _save_state({"last_pass_signature": sig, "fail_streak": 0})
        print("[build-gate] ✅ 빌드 게이트 통과 — 멈춤 허용.", file=sys.stderr)
        _allow()

    # 실패 처리
    fail_streak = int(state.get("fail_streak", 0)) + 1
    _save_state(
        {"last_pass_signature": state.get("last_pass_signature", ""), "fail_streak": fail_streak}
    )

    if fail_streak > MAX_FAIL_STREAK:
        _save_state({"last_pass_signature": state.get("last_pass_signature", ""), "fail_streak": 0})
        print(
            f"[build-gate] ⚠️ 빌드가 {MAX_FAIL_STREAK}회 연속 실패했습니다. "
            "자동 수정 루프를 중단하고 사용자 개입을 위해 멈춤을 허용합니다.\n"
            "남은 실패 내용:\n" + report,
            file=sys.stderr,
        )
        _allow()

    reason = (
        "빌드 게이트가 실패했습니다. 아래 실패를 직접 고친 뒤 작업을 계속하세요. "
        f"(자동 수정 시도 {fail_streak}/{MAX_FAIL_STREAK})\n\n"
        f"{report}\n\n"
        "수정 지침: 실패한 게이트의 출력을 읽고 근본 원인을 고치세요. "
        "포맷은 `ruff format .`, 안전한 린트는 `ruff check --fix .` 로 정리할 수 있습니다. "
        "테스트/타입 오류는 코드를 수정해 해결하세요. 검증을 우회하지 마세요."
    )
    _block(reason)


if __name__ == "__main__":
    main()
