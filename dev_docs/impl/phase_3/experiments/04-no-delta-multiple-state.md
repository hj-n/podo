# Experiment 04 — No Delta and Multiple State

## Question

변화 없는 capture는 permanent Context를 바꾸지 않고, 하나의 Event는 필요한 여러 State에만 영향을 줄 수 있는가?

## Setup

한 capture는 `context discard --reason no-delta`로 처리하고 permanent Context 전후 hash를 비교했다. 다른 capture는 서로 다른 두 `state_slug` update를 한 request에 넣었다.

## Expected

No Delta는 receipt만 만들고, multi-State request는 Event 하나와 State별 Delta를 만든다.

## Result

Pass. No Delta는 inbox original을 정리하고 작은 receipt만 남겼으며 Event·Delta·State hash를 바꾸지 않았다. Multi-State request는 Event 하나, State별 Delta 두 개와 State 두 개를 만들었다.

## Evidence

- No Delta outcome: `no-delta`
- Multi-State shape: 1 Event → 2 Delta → 2 State
- 각 State link가 자신의 Delta를 가리키고 두 Delta가 같은 Event를 참조함

## Decision

No Delta는 permanent Context update가 아니다. 하나의 원본이 여러 주제에 영향을 주면 Event를 복사하지 않고 State마다 별도 Delta를 둔다.
