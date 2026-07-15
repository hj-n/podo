# Experiment 05 — Recovery Planner

## Question

추측 없이 실행 가능한 hash-pinned 복구 계획과 사용자 판단이 필요한 문제를 구분할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `podo recover --json` creates one plan artifact per unfinished transaction without changing Context or transaction evidence.
- The plan pins `plan.json`, `journal.json`, staged/original evidence, every target and post-validation cleanup source by type, mode and content hash.
- Missing or exact staged targets are classified as mechanically resumable.
- Strictly non-overlapping State changes remain resumable, while overlapping changes produce `manual-confirmation-required` with an explicit reason.
- No unfinished transaction returns `nothing-to-recover` without creating artifacts.

## Boundary

Plan creation may write only `.podo-work/recovery-plans/<plan-id>.json`. It does not mean approval and never resumes a transaction.
