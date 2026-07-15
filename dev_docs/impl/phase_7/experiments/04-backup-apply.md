# Experiment 04 — Backup and Journaled Migration Apply

## Question

Exact plan 뒤 staged migration을 실행하고, 성공 시 backup을 보존하며, 모든 handled apply failure에서 이전 제품과 사용자 데이터를 함께 복원할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- An exact plan migrated synthetic product 0.9.0 / Workspace 1 to product 1.0.0 / Workspace 2.
- Migration ran against a complete staged Workspace and preserved the State file mode.
- Unlisted `user_config.md` bytes and mode remained unchanged.
- Backup retained the previous three product roots, `WORKSPACE_VERSION`, original State and a complete manifest.
- Changing affected State after planning produced `E_MIGRATION_PLAN_STALE` before backup.
- A failing entrypoint retained the current Workspace and a complete backup.
- An entrypoint changing unlisted user config produced `E_MIGRATION_UNDECLARED_CHANGE` before apply.
- Nine injected apply failures restored exact product and user snapshots.
- `python3 tests/run_phase7_migration.py`

## Decision

Backup is created after all pins and target identity are revalidated but before staged migration code runs. A complete matching backup may be reused for a retry and is never deleted automatically.
