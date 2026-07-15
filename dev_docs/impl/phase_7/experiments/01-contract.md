# Experiment 01 — Migration Contract

## Question

일반 update와 별도 승인 migration을 기계적으로 구분하고 제품과 사용자 데이터를 함께 복원할 계약을 정의할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `product/.podo/contracts/workspace_migrations.json`
- `product/.podo/migrations/README.md`
- `python3 tests/run_phase7_contracts.py`

Current product 0.6.0 candidate remains compatible only with Workspace 1 and contains no numbered migration directory. The contract separates normal update, exact migration apply and separately approved full rollback.
