# Experiment 01 — Transaction Contract

## Question

Event, Delta, State와 receipt를 하나의 관찰 가능한 transaction으로 준비할 수 있는가?

## Status

Passed.

## Setup

- 기존 `context apply`의 Event, Delta, State와 receipt 생성을 transaction stage로 이동했다.
- transaction plan에 target, staged hash, 기존 State hash와 cleanup source를 기록했다.
- journal에 실제 filesystem 적용 단계만 기록했다.

## Result

- 정상 apply는 모든 파일을 준비하고 검증한 뒤 Event → Delta → State → receipt 순서로 적용했다.
- 완료 후 staged transaction은 제거되고 작은 transaction receipt가 남았다.
- 기존 Context file 형식, links와 idempotent apply는 유지됐다.
- 제품 contract `transactions.json`이 journal 상태, commit 순서와 State hash 재검사를 고정한다.

## Evidence

```text
python3 tests/run_phase5_transactions.py
PASS normal Context apply commits from a prepared transaction
```

Phase 3 context regression도 함께 통과했다.

## Decision

Transaction ID는 source capture에 대해 결정적으로 만든다. 같은 capture에 unfinished transaction이 있으면 새 apply를 만들지 않고 recovery로 보낸다.
