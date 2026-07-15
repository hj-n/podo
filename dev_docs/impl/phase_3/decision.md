# Phase 3 Gate Decision

- Decision: GO
- Decided: 2026-07-15
- Evidence: `experiments/` and `findings.md`

## Reason

Supported Codex runtime의 exact Stop transcript가 atomic inbox capture로 저장되고, 다음 Interface 작업이 의미 있는 capture만 Event·Delta·State로 적용했다. Synthetic suite는 identity, completeness, immutable original, idempotency, No Delta, multi-State와 주요 failure를 통과했다.

Desktop의 네 실제 Codex 작업에서도 capture → apply → No Delta → State-first restore가 재현됐다. 사용자는 과거 결정을 다시 설명하지 않았고, 마지막 restore는 Delta와 Event를 읽지 않았다. 모든 test artifact는 marker 확인 뒤 제거됐다.

## Conditions or Required Changes

- `0.144.0-alpha.4` 외 runtime은 지원을 추측하지 않고 fail closed한다.
- Pending capture는 다음 Interface 작업에서 처리되므로 한 turn 지연이 있다.
- Partial capture는 Event·Delta·State apply에 사용하지 않는다.
- Concurrent conflict는 stale hash로 중단하며 Phase 5 전에는 자동 병합하지 않는다.
- Actual personal data 사용, GitHub release, update와 migration은 아직 승인된 범위가 아니다.

## Next Phase

Phase 4 — Conversation and Decision Policies.
