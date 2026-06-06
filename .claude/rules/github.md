# GitHub / Git 규칙

## 저장소 / 계정

- **원격 저장소**: https://github.com/do-heewan/Noh-Base-BE (`origin`, private)
- **계정**: GitHub ID `do-heewan` / `nhw3152@gmail.com`
- 로컬 git 사용자(repo-local): `user.name=do-heewan`, `user.email=nhw3152@gmail.com`
  - 전역(`--global`) 설정은 건드리지 않는다. 이 저장소 안에서만 위 신원을 쓴다.

## 커밋

- **사용자가 명시적으로 요청할 때만** 커밋·push 한다. 임의로 커밋하지 않는다.
- 커밋 메시지는 **한국어**, `type: 요약` 형태. type 예: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`.
- 본문이 필요하면 변경 이유/맥락을 불릿으로. 커밋 메시지 끝에 항상 다음 트레일러를 붙인다:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **커밋 전 빌드 게이트가 초록인지 확인**한다(`.claude/hooks/verify_build.py`). 깨진 상태로 커밋하지 않는다.

## 브랜치 / push

- 기본 브랜치는 `main`. 기능 작업은 가능하면 `feat/<주제>` 브랜치에서 하고 PR로 합친다(솔로 MVP 단계에선 main 직접 작업도 허용).
- `main` 에 force-push 금지. 히스토리 재작성(rebase/amend)은 **아직 push 안 된 로컬 커밋**에 한해서만.
- push 후 충돌 시 `git pull --rebase origin main` 으로 정리한 뒤 다시 push.

## 절대 커밋 금지 (비밀)

- `serviceAccountKey.json`, `firebase-credentials.json`, `.env`, `.env.*` (`.env.example` 제외) — `.gitignore` 에 등록돼 있다.
- API 키·토큰·서비스 계정 JSON 을 코드/커밋/PR 본문에 넣지 않는다. 설정은 `app/core/config.py` 의 `Settings` 로만 읽는다.
- 실수로 스테이징되면 `git rm --cached <파일>` 로 빼고 `.gitignore` 를 보강한다.

## 도구 메모

- `gh` CLI 는 현재 미설치. 레포 생성/PR을 CLI로 하려면 `winget install --id GitHub.cli` 후 `gh auth login`.
- 원격이 끊겨 있으면: `git remote add origin https://github.com/do-heewan/Noh-Base-BE.git`
