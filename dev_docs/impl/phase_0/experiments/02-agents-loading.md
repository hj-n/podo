# Experiment 02 — AGENTS Loading

## Question

User Workspace의 작은 `AGENTS.md`가 새 Codex 작업에 자동 적용되고 개발 역할과 분리되는가?

## Setup

The disposable User Workspace received a minimal root `AGENTS.md` and `user_config.md`.

- V1 instruction: for `진단: 역할`, answer `INTERFACE_V1|포도랩|차분하고 간결함`.
- The initial prompt contained only `진단: 역할`; it did not repeat the role, name or personality.
- After the first task, only the marker in `AGENTS.md` was changed from V1 to V2.
- A separate new task and a resume of the V1 thread then received the same diagnostic prompt.
- `codex exec --json` captured the observable task trace.

## Expected

합성 marker와 Interface 역할이 별도 prompt 없이 적용되고, instruction 변경은 새 작업에서 확실히 반영된다.

## Result

Pass on the tested CLI runtime.

- First new task: `INTERFACE_V1|포도랩|차분하고 간결함`
- New task after the edit: `INTERFACE_V2|포도랩|차분하고 간결함`
- Resumed V1 thread after the edit: `INTERFACE_V2|포도랩|차분하고 간결함`

The first trace shows that the agent read `user_config.md` before the final diagnostic response. The Development Workspace instruction did not appear because the test used a separate directory and isolated Codex home.

## Evidence

- First thread id: `019f63da-ea6b-7683-b7e2-766a0d4fb3f7`
- The first JSONL trace recorded `thread.started`, `turn.started`, a `user_config.md` read, the exact final agent message and `turn.completed`.
- V1 and V2 final outputs differed only where `AGENTS.md` changed.
- Resume loaded V2, showing that this runtime rebuilds applicable project instructions when a persisted thread is resumed through a new CLI invocation.

## Decision

A small User Workspace `AGENTS.md` is a viable Interface entrypoint. New tasks reliably load it, and resume is not assumed to keep a stale copy on this runtime. A task already in the middle of one turn was not mutated for this test; Podo updates should still instruct the user to start a new task so the policy boundary is obvious and portable across surfaces.
