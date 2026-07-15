# Experiment 06 — CLI, Policy and Diagnosis

## Question

일반 update와 별도 migration approval을 canonical CLI에서 구분하고 unfinished migration을 doctor와 task startup에 표시할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `podo update --version 1.0.0` rejected an incompatible Workspace before creating migration plan or backup.
- `podo migrate --version`, exact `migrate --apply`, `migrate rollback --backup` and exact rollback apply completed a synthetic round trip.
- An unfinished migration produced `PODO_D320_MIGRATION_INCOMPLETE` in doctor and startup `recovery_diagnosis`.
- Startup JSON exposed `migration_recovery_required` separately from Context and product update recovery.
- Product update returned `E_MIGRATION_RECOVERY_REQUIRED` while the journal remained.
- Product policy distinguishes normal update request, migration plan review, exact apply and separately planned full rollback.
- `python3 tests/run_phase7_cli.py`

## Decision

The canonical user surface remains one `podo` entrypoint. Migration and full rollback are two-step operations, while doctor only diagnoses interrupted migration and does not claim automatic semantic recovery.
