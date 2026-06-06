#!/usr/bin/env python
"""빌드/검증 게이트 — 이 프로젝트에서 '빌드'의 단일 기준.

순서대로 다음을 실행하고 결과를 요약한다:
  1. ruff format --check   (포맷)
  2. ruff check            (린트)
  3. mypy                  (타입)
  4. pytest                (테스트)
  5. import smoke          (FastAPI 앱 기동 가능 여부)

단독 실행:
    conda run -n Noh_Base_BE python .claude/hooks/verify_build.py
    # 빠른 검사(테스트 제외): --fast

종료 코드: 모든 게이트 통과 시 0, 하나라도 실패 시 1.
Stop 훅(stop_gate.py)이 run_gate() 를 호출해 자동 수정 루프를 돌린다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _tool_cmd(tool: str) -> list[str]:
    """env 의 콘솔 스크립트를 우선 사용하고, 없으면 python -m 으로 폴백."""
    bindir = Path(sys.executable).parent
    for cand in (bindir / f"{tool}.exe", bindir / "Scripts" / f"{tool}.exe", bindir / tool):
        if cand.exists():
            return [str(cand)]
    return [sys.executable, "-m", tool]


@dataclass
class StepResult:
    name: str
    ok: bool
    output: str


def _run(name: str, cmd: list[str]) -> StepResult:
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return StepResult(name=name, ok=proc.returncode == 0, output=output.strip())


def run_gate(fast: bool = False) -> tuple[bool, str]:
    """모든 게이트를 실행하고 (통과여부, 사람이 읽는 리포트) 반환."""
    ruff = _tool_cmd("ruff")
    mypy = _tool_cmd("mypy")
    pytest = _tool_cmd("pytest")

    steps: list[StepResult] = []
    steps.append(_run("format (ruff format --check)", [*ruff, "format", "--check", "."]))
    steps.append(_run("lint   (ruff check)", [*ruff, "check", "."]))
    steps.append(_run("types  (mypy)", [*mypy]))
    if not fast:
        steps.append(_run("tests  (pytest)", [*pytest]))
    steps.append(
        _run(
            "smoke  (import app.main)",
            [sys.executable, "-c", "import app.main; print('app import ok')"],
        )
    )

    all_ok = all(s.ok for s in steps)
    lines: list[str] = []
    for s in steps:
        lines.append(f"[{'PASS' if s.ok else 'FAIL'}] {s.name}")
    report = ["=" * 60, "빌드 게이트 결과", "=" * 60, *lines]
    if not all_ok:
        report.append("")
        report.append("실패 상세:")
        for s in steps:
            if not s.ok:
                report.append("-" * 60)
                report.append(f"# {s.name}")
                report.append(s.output or "(출력 없음)")
    report.append("=" * 60)
    return all_ok, "\n".join(report)


def main() -> int:
    fast = "--fast" in sys.argv
    ok, report = run_gate(fast=fast)
    sys.stdout.write(report + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    # Windows 콘솔에서 UTF-8 출력 보장
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
