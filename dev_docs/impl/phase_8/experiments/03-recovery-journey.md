# Experiment 03 — Failure and Recovery Journey

## Question

정상 Context에서 concurrent stale write와 중단된 transaction이 연속으로 발생해도 현재 State를 보존하고, 진단과 exact approval 뒤에만 복구할 수 있는가? 원본 누락과 깨진 link도 자동 transaction recovery와 구분되는가?

## Setup

- Product 0.6.0 Release package로 설치한 새 temporary Workspace
- 하나의 `state/recovery-planning.md`를 기준으로 한 두 concurrent request
- `after-delta-1` Context failure injection
- 정상 복구 Workspace를 복제한 뒤 Event original과 State link를 손상시킨 별도 fixture
- `tests/run_phase8_recovery.py --run-id verification-1`

## Result

Passed on 2026-07-15.

- 첫 concurrent request만 적용됐고 같은 baseline hash를 사용한 두 번째 request는 `E_STATE_STALE`로 permanent Context 변경 없이 거부됐다.
- Delta boundary 직후 중단된 transaction은 current State를 이전 winner로 유지하고 journal과 staging evidence를 남겼다.
- Doctor는 `PODO_D001_TRANSACTION_INCOMPLETE`를, inbox startup은 `recovery_required`와 같은 read-only diagnosis를 제공했다.
- Recovery planning 전후 transaction과 Context evidence가 같았고 recovery plan artifact만 추가됐다.
- Exact plan apply가 staged State를 완료하고 transaction을 제거했으며 post-recovery doctor는 healthy였다.
- 별도 damage fixture에서 missing original은 `PODO_D100_E_EVENT_ORIGINAL`, broken link는 `PODO_D100_E_STATE_LINK`로 구분됐다.
- Damage doctor는 read-only였고 일반 `podo recover`는 `nothing-to-recover`를 반환해 의미를 추측하지 않았다.

## Evidence

- `tests/run_phase8_recovery.py`
- Stable step IDs: `recovery-baseline`, `stale-concurrency`, `interruption-diagnosis`, `exact-recovery`, `damage-diagnosis`, `recovery-final`
- Recovered State hash: `eec50df4571982564956ecdb931f328c7ad857165a0b07bb232b36964a5009f9`

## Decision

Recovery journey를 Phase 8 canonical suite에 포함한다. 실제 Codex가 recovery diagnosis를 설명하고 exact plan 적용 전에 승인을 멈추는지는 별도 real acceptance에서 확인한다.
