# Experiment 03 — Concurrent State Changes

## Question

동시 변경을 오래된 State로 덮어쓰지 않고 비충돌과 충돌을 구분할 수 있는가?

## Status

Passed.

## Setup

- Transaction A를 prepared 상태에서 멈췄다.
- 같은 base State를 기준으로 Transaction B를 먼저 완료했다.
- A와 B가 서로 다른 State 영역을 수정하는 경우와 같은 결정 줄을 수정하는 경우를 각각 재개했다.

## Result

- base/current/proposed의 line changes가 겹치지 않으면 strict 3-way merge가 두 marker와 Delta link를 모두 보존했다.
- merged State는 TODO/date/link validator를 통과한 뒤 atomic하게 적용됐다.
- 같은 결정 줄의 변경은 `E_STATE_CONFLICT`로 중단됐다.
- 충돌 시 먼저 완료된 current State bytes는 그대로 유지됐고 transaction journal은 recovery-required를 기록했다.

## Evidence

```text
python3 tests/run_phase5_concurrency.py
PASS non-overlapping concurrent State changes merge and validate
PASS overlapping concurrent State changes preserve current State and require recovery
```

## Decision

자동 병합은 line changes가 엄격히 비중첩이고 merged State 전체가 유효할 때만 허용한다. 의미가 겹치는 결정이나 TODO 변경은 사용자 확인 없이 병합하지 않는다.
