# Experiment 06 — Approved Recovery Apply

## Question

승인된 plan만 stale state를 재검증해 적용하고 재실행을 안전하게 처리하는가?

## Status

Passed on 2026-07-15.

## Evidence

- `podo recover --apply <plan-id>` rechecks every pinned path before entering the existing journaled commit.
- A one-byte State change after planning returns `E_RECOVERY_PLAN_STALE` without touching transaction evidence.
- The exact approved plan resumes Event → Delta → State → receipts → validation → cleanup and records its applied result.
- Repeating an applied plan returns `already-applied` without modifying Context.
- A manual conflict plan cannot be applied even when its plan ID is passed.
- A forced failure between the current and deferred resolution receipts is recovered by writing the second receipt before validated cleanup.

## Command

```bash
python3 tests/run_phase5_recovery.py
```
