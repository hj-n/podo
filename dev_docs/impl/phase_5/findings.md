# Phase 5 Findings

Phase 5 실험 결과를 confirmed evidence와 limitation으로 기록한다.

## Confirmed

- `doctor` is read-only across healthy, interrupted and damaged synthetic Workspaces.
- Unfinished transactions are surfaced at task startup through `recovery_required`; they are not auto-applied or deleted.
- Product drift and user Context damage use distinct finding codes so recovery policy does not mistake one for the other.
- Recovery planning changes only its own plan artifact and pins all evidence, targets and cleanup sources.
- Recovery apply requires an exact safe plan ID, rejects stale pins, is idempotent after success and refuses overlapping State conflicts.
- The two-receipt deferred resolution boundary resumes from its journal without duplicating or skipping a receipt.
