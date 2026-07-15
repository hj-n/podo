# Experiment 03 — Conflict and Correction

## Question

명확한 결정 변경은 정정 기록과 함께 반영하고 모호한 충돌은 기존 State를 보존하는가?

## Status

Passed for the storage lifecycle; real Codex policy acceptance remains.

## Setup

- 오전 9시라는 기존 State가 있는 Workspace에서 “10시로 옮길 가능성”을 deferred로 만들었다.
- deferred capture를 직접 apply하려는 우회와 request 없는 confirmation을 시도했다.
- 명확한 후속 confirmation과 correction request로 기존 State를 갱신했다.

## Expected

- 모호한 충돌 동안 기존 State가 유지된다.
- deferred capture는 직접 apply 또는 discard할 수 없다.
- 명확한 정정은 새 결론을 State에 반영하고 이전 결론과 변경 이유를 Delta에 남긴다.

## Result

- 직접 apply는 `E_CAPTURE_DEFERRED`, request 없는 확인은 `E_RESOLUTION_REQUEST`로 실패했고 permanent Context hash가 유지됐다.
- 확인 후 State에는 오전 10시 결정이 남고 기존 오전 9시 결정은 현재 결론에서 제거됐다.
- 새 Delta에는 이전 오전 9시 결정과 오전 10시 정정이 함께 기록됐다.
- 과거 Event와 Delta는 수정되지 않았다.

## Evidence

`tests/run_phase4_decisions.py`가 State와 Delta의 이전·현재 결정 marker를 확인한다.

## Decision

충돌의 모호함을 State 변경으로 표현하지 않는다. 기존 State를 유지한 deferred lifecycle과 명확한 후속 resolution을 사용한다.
