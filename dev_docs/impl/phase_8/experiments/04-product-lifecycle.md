# Experiment 04 — Product Lifecycle Journey

## Question

이미 유효한 사용자 Context가 있는 한 Workspace에서 compatible update/rollback, incompatible update rejection, migration failure/success와 full rollback을 차례로 실행해도 소유권과 승인 경계가 유지되는가?

## Setup

- Synthetic product 0.8.0 / 0.9.0: Workspace 1 compatible
- Synthetic product 1.0.0 / 1.0.1: Workspace 2 compatible, verified 1→2 migration 포함
- 1.0.1 migration entrypoint는 staging에서 의도적으로 실패
- `state/project.md`에 `PRODUCT_LIFECYCLE_CONTEXT` marker와 linked Event/Delta 존재
- `tests/run_phase8_product_lifecycle.py --run-id verification-1`

## Result

Passed on 2026-07-15.

- 0.8.0→0.9.0 compatible update와 exact 0.8.0 rollback은 `user_config.md`, `WORKSPACE_VERSION`, Event, Delta, State의 bytes와 mode를 유지했다.
- 1.0.0 normal update는 `E_WORKSPACE_INCOMPATIBLE`로 멈췄고 migration plan이나 backup을 만들지 않았다.
- 1.0.1 exact migration apply는 entrypoint failure 뒤 product 0.8.0, Workspace 1과 모든 user evidence를 복원하고 complete backup을 남겼다.
- 별도 1.0.0 plan/apply는 product와 Workspace를 함께 1.0.0/2로 옮기고 기존 Context marker를 보존했다.
- Full rollback review는 non-applying이었고 exact apply는 product 0.8.0, Workspace 1과 원래 user evidence를 복원했다.
- 실패 전 backup, 성공 migration source backup과 rollback-start safety backup 세 개가 모두 complete 상태로 남았다.
- 최종 validator와 doctor가 통과했다.

## Evidence

- `tests/run_phase8_product_lifecycle.py`
- Stable step IDs: `product-baseline`, `compatible-update-rollback`, `incompatible-update-stop`, `migration-failure-restore`, `migration-success`, `full-rollback`, `product-final`

## Decision

Product lifecycle journey를 Phase 8 canonical suite에 포함한다. 이 결과는 infrastructure 검증이며 실제 Workspace format 2, production migration 또는 public Release 채택을 의미하지 않는다.
