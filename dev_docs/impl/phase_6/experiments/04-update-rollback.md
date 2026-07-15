# Experiment 04 — Update and Rollback

## Question

제품 세 경로만 transaction으로 교체하고 중간 실패 시 이전 제품을 정확히 복원할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `AGENTS.md`, `.codex` and `.podo` are staged and backed up under one `.podo-work/product-updates/<id>/` journal.
- Compatible `0.4.0 → 0.4.1` update and exact `0.4.1 → 0.4.0` rollback preserve user-owned sentinel content and mode.
- Failure injection after prepare, after each of three backups, after each of three installs and before/after final validation restores the exact previous product snapshot.
- Rolled-back failures leave a small receipt and no active transaction directory.
- Product hash drift, unfinished Context recovery and incompatible Workspace version stop before product replacement.
- Successful output includes release notes plus explicit new-Codex-task and hook-review guidance.

## Command

```bash
python3 tests/run_phase6_product_update.py
```
