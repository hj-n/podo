# Experiment 02 — Resolution Evidence

## Question

확인 turn과 원래 보류 turn의 전체 원본을 하나의 resolution Event에서 추적할 수 있는가?

## Status

Passed.

## Setup

- 기존 결정을 바꿀 가능성이 있는 첫 capture를 deferred로 만들었다.
- 별도의 confirmation capture로 `context resolve --decision confirmed`를 실행했다.
- 별도의 deferred/answer 쌍은 `rejected`로 request 없이 닫았다.

## Expected

- confirmed resolution은 confirmation turn을 주 Event로 사용한다.
- 같은 Event 안에서 deferred turn의 exact original도 추적할 수 있다.
- rejected resolution이 미래 Context에 중요하지 않으면 permanent Context를 만들지 않는다.
- 재실행은 중복 Event나 receipt를 만들지 않는다.

## Result

- Event의 `original/session.jsonl`은 confirmation capture와 byte 단위로 같았다.
- `original/related/<deferred-id>/session.jsonl`은 deferred capture와 byte 단위로 같았다.
- Metadata의 `Resolution`, `Resolves-Capture`, related original path와 hash가 연결됐다.
- 두 receipt는 `resolved_by_capture`와 `resolution_of`로 서로 연결됐다.
- rejection은 Event, Delta와 State hash를 바꾸지 않았다.
- 재실행은 `already-resolved`를 반환했다.

## Evidence

```text
python3 tests/run_phase4_decisions.py
PASS confirmed resolution preserves confirmation and deferred originals
PASS rejected resolution closes both captures without permanent Context change
```

## Decision

confirmation만 단독 근거로 남기지 않는다. resolution Event에 confirmation 원본을 주 entrypoint로 두고, 무엇을 확인했는지 담긴 deferred 원본을 related original로 함께 보존한다.
