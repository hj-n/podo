# Experiment 02 — Everyday User Journey

## Question

설치, 명시적 개인화, Context 생성, No Delta, 불확실한 충돌 해결과 TODO lifecycle이 하나의 Workspace에서 이전 단계의 실제 결과를 이어받아 동작하는가?

## Setup

- `tools/build_release.py`가 만든 unpublished product 0.6.0 package
- 새 temporary Workspace와 synthetic Codex transcript originals
- 한 `state/orchard-planning.md`를 모든 결정·TODO step에서 계속 사용
- `tests/run_phase8_everyday.py --run-id verification-1`

## Expected

- Product 0.6.0과 Workspace 1로 빈 설치가 완료된다.
- 개인화는 `user_config.md`만 바꾸고 Context는 만들지 않는다.
- 명확한 첫 결정과 TODO가 하나의 Event, Delta와 State로 연결된다.
- No Delta와 불확실한 충돌은 permanent Context를 바꾸지 않는다.
- 후속 확인은 보류 original과 확인 original을 함께 보존한다.
- TODO 완료, 취소와 재개 날짜가 유효하고 최종 doctor가 healthy다.

## Result

Passed on 2026-07-15.

- Package install에서 product 0.6.0 / Workspace 1을 확인했다.
- 명시적 비서 이름, 성격과 응답 선호를 기록해도 Event·Delta·State는 생기지 않았다.
- 첫 Context는 exact transcript original 하나, linked Delta 하나와 State 하나로 승격됐다.
- No Delta 전후 permanent Context hash가 같았다.
- 미확정 시간 변경은 기존 결정을 유지한 채 deferred record만 만들었다.
- 후속 확인 Event는 현재 original과 deferred original을 모두 exact bytes로 보존하고 기존 결정을 교체했다.
- TODO 완료는 Created/Due/Completed/Result를, 취소 후 재개는 Created/Cancelled/Reopened를 함께 보존했다.
- 최종 State hash는 `6f9b2411ae42fef8bb6815357a16271ba7ded1dc394a19dbe93b657c2ede6d65`였고, 여섯 lifecycle receipt, empty pending/deferred inbox와 healthy doctor를 확인했다.

## Evidence

- `tests/phase8_support.py`
- `tests/run_phase8_everyday.py`
- `PHASE8_SUMMARY` schema 1의 stable step IDs: `install`, `personalize`, `first-context`, `no-delta`, `defer-conflict`, `resolve-conflict`, `todo-lifecycle`, `final-health`

Temporary Workspace와 package는 context manager 종료 시 제거됐으며 저장소에는 transcript 원문이나 사용자 데이터가 추가되지 않았다.

## Decision

Everyday journey는 Phase 8의 첫 vertical slice로 채택한다. 실제 Codex가 State-first로 읽고 사용자 설정을 응답에 적용하는지는 synthetic harness의 직접 파일 검증으로 대신하지 않고 Step 8.6에서 별도로 검증한다.
