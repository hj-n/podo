# Experiment 03 — Event, Delta, and State Apply

## Question

Meaningful capture를 하나의 Event, traceable Delta와 자유 형식 State로 안전하게 적용할 수 있는가?

## Setup

Complete capture와 자유 형식 `state_markdown` request를 `podo context apply`에 전달했다. Writer는 Event와 Delta link, State의 `{{DELTA_LINK}}`, Updated와 TODO date를 preflight하고 Event → Delta → State 순서로 적용했다.

## Expected

Event → Delta → State 순서와 link가 유효하며 반복 적용은 duplicate를 만들지 않는다.

## Result

Pass. Full original bytes를 가진 Event 하나, Delta 하나와 State 하나가 생성됐고 installed validator가 전체 link와 TODO를 통과시켰다. 같은 capture를 다시 적용하면 receipt를 찾아 `already-processed`로 끝났다.

## Evidence

- Command: `python3 tests/run_phase3_context.py`
- Product version: `0.2.0`, Workspace version: `1`
- TODO: Created와 Due 날짜 검증
- Existing State: expected SHA-256 일치 필수
- Final validation: `OK mode=context-present`

## Decision

State를 고정된 기억 category로 제한하지 않고 완성된 Markdown candidate로 받는다. Writer는 형식, source와 link를 강제하고 의미 판단과 실제 문장 구성은 Interface Codex가 담당한다.
