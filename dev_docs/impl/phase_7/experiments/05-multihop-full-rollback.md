# Experiment 05 — Multi-hop and Full Rollback

## Question

여러 Workspace version을 순서대로 이전하고, 성공 후 별도 승인된 full rollback으로 이전 제품과 사용자 데이터를 함께 복원할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- A unique synthetic 1→2→3 chain executed `1-to-2` before `2-to-3` and reached product 2.0.0 / Workspace 3.
- A separately generated rollback plan reported a State change made after migration.
- Exact rollback approval restored product 0.9.0, Workspace 1 and original State hash/mode.
- The original pre-migration backup and pre-rollback safety backup both remained.
- Changing State after rollback planning produced `E_ROLLBACK_PLAN_STALE` before safety backup.
- Nine rollback failure injection points restored the exact product 1.0.0 / Workspace 2 rollback-start snapshot.
- `python3 tests/run_phase7_rollback.py`

## Decision

Full rollback is a new destructive operation, not a continuation of migration approval. User changes made since migration are shown in the rollback plan and preserved in a safety backup before overwrite.
