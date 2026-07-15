# Experiment 01 — Disposable Workspace

## Question

실제 사용자 데이터와 분리된 합성 User Workspace를 반복해서 만들 수 있는가?

## Setup

- Date: 2026-07-15 KST
- Host: macOS, Codex desktop installed as `/Applications/ChatGPT.app`
- Runtime: bundled `codex-cli 0.144.0-alpha.4`
- Disposable root: `/tmp/podo-phase0.hoHZa7`
- User Workspace: `/tmp/podo-phase0.hoHZa7/user-workspace`
- Isolated Codex home: `/tmp/podo-phase0.hoHZa7/codex-home`
- Authentication: the isolated home links only the existing local `auth.json`; it does not link existing sessions, history, state, memories, config or global `AGENTS.md`.
- All prompts and files contain synthetic diagnostic markers only.

The Homebrew command at `/opt/homebrew/bin/codex` was also checked before selecting the runtime.

## Expected

저장소 밖의 새 디렉터리에서 Codex 버전과 실행 surface를 기록하고, 기존 사용자 파일을 읽지 않는다.

## Result

Pass with one environment finding.

The disposable Workspace and isolated session store were created outside `realpodo`. A new synthetic Codex session was written only below the isolated `codex-home/sessions/` path.

The Homebrew `codex` symlink was broken because it pointed to a missing `0.128.0` binary. The desktop bundle contained a working `0.144.0-alpha.4` binary, so all experiments use that exact binary rather than silently depending on `PATH`.

## Evidence

- `codex --version` returned `codex-cli 0.144.0-alpha.4` for the bundled binary.
- `codex login status` under the isolated home returned `Logged in using ChatGPT`.
- The first synthetic session was stored at `codex-home/sessions/2026/07/15/rollout-...jsonl`.
- No existing `$HOME/.codex/sessions` file was enumerated or opened.

## Decision

Use the desktop-bundled binary by absolute path for Phase 0 reproducibility. Record the exact runtime version in every transcript result. Treat the broken Homebrew symlink as a local setup issue, not a Podo feasibility failure.
