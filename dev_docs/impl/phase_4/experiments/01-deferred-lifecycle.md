# Experiment 01 — Deferred Lifecycle

## Question

확인이 필요한 capture를 permanent Context 변경 없이 한 번만 보류하고 이후 확인 또는 기각과 연결할 수 있는가?

## Status

Passed.

## Setup

- 합성 Workspace의 기존 State와 permanent Context hash를 기준점으로 잡았다.
- complete capture를 `podo context defer`로 보류했다.
- 같은 capture를 다시 보류하고 invalid State 후보와 partial capture를 각각 주입했다.

## Expected

- defer는 Event, Delta와 State를 바꾸지 않는다.
- deferred capture는 일반 pending에서 빠지고 deferred 목록에 한 번만 나타난다.
- invalid request와 partial capture는 permanent Context를 바꾸지 않고 원본 capture를 유지한다.

## Result

- complete capture는 `.podo-work/deferred/`에 한 번만 기록됐다.
- `podo inbox --json`은 `pending`과 `deferred`를 구분했다.
- idempotent 재실행은 `already-deferred`를 반환했다.
- invalid State 후보는 `E_REQUEST_STATE`, partial capture는 `E_CAPTURE_PARTIAL`로 실패했다.
- 모든 경로에서 기존 Event, Delta와 State hash가 유지됐다.

## Evidence

```text
python3 tests/run_phase4_decisions.py
PASS uncertain conflict defers once without permanent Context change
PASS invalid defer request preserves pending capture
PASS partial capture cannot become a deferred decision
```

Phase 3 context regression suite도 함께 통과했다.

## Decision

보류 상태는 permanent State의 `Needs Confirmation`을 강제로 만들지 않고 `.podo-work/deferred/`에서 관리한다. 일반 pending과 분리해 새 task마다 같은 질문이 처리 대상으로 반복되지 않게 한다.
