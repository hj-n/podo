# Experiment 04 — TODO Lifecycle

## Question

자연어 TODO의 위치와 생성·마감·완료·취소·재개 날짜를 일관되게 관리할 수 있는가?

## Status

Passed for lifecycle storage and validation; real Codex natural-language acceptance remains.

## Setup

- 한 State의 TODO를 생성하고 Due를 추가했다.
- 같은 TODO를 결과와 함께 완료했다.
- 별도 TODO를 취소한 뒤 다시 열었다.
- terminal 날짜가 없는 checked TODO를 writer에 주입했다.

## Expected

- Created는 항상 있고 Due는 명시된 경우에만 있다.
- checked TODO는 Completed 또는 Cancelled 중 하나를 가진다.
- terminal 이력이 있는 open TODO는 Reopened를 가진다.
- invalid lifecycle은 기존 State를 보존한다.

## Result

- create, due, complete, cancel과 reopen State가 writer와 Workspace validator를 모두 통과했다.
- 완료 Result와 취소 Result가 사람이 읽을 수 있는 State에 남았다.
- terminal 날짜가 없는 checked TODO는 `E_REQUEST_TODO_LIFECYCLE`로 실패했고 기존 State bytes가 유지됐다.

## Evidence

```text
python3 tests/run_phase4_todo.py
PASS TODO create, due, complete, cancel and reopen lifecycle
PASS invalid TODO lifecycle preserves current State
```

## Decision

취소도 닫힌 TODO로 표현하되 `Completed`와 섞지 않는다. 재개는 이전 terminal 이력을 지우지 않고 `Reopened` 날짜로 현재 open 상태를 설명한다.
