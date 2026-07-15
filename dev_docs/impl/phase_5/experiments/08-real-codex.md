# Experiment 08 — Real Codex Recovery Acceptance

## Question

실제 새 Codex task에서도 진단, 설명, 승인, 복구와 State-first continuity가 이어지는가?

## Status

Passed on 2026-07-15.

## Evidence

`python3 tests/run_phase5_codex_acceptance.py` passed across seven real Codex tasks in a marker-owned Desktop Workspace with isolated `CODEX_HOME`.

1. A clear baseline decision was captured and applied.
2. A second confirmed decision was captured.
3. `after-delta-1` forced an interrupted transaction while baseline State remained current.
4. The next task received the inbox-generated read-only `recovery_diagnosis`, explained it at high level and did not apply recovery.
5. Permanent Context and the unfinished transaction remained unchanged before approval.
6. An explicit user approval caused recovery planning and exact plan-ID apply.
7. The following task restored the recovered marker from State without reading permanent Event or Delta history.

Every run, including failed harness iterations, verified its marker before deleting the Workspace and isolated Codex home. The Desktop test parent was left absent or empty.

## Finding

Relying on Interface Codex to make a separate `doctor` call after seeing `recovery_required` was not deterministic. `podo inbox --json` therefore runs the same read-only doctor engine automatically and includes `recovery_diagnosis`; standalone `podo doctor` remains available for repeat diagnosis.
