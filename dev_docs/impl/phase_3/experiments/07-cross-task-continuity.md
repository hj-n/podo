# Experiment 07 — Cross-task Continuity

## Question

두 번째 Codex task가 이전 capture를 적용하고 State-first로 결정과 TODO를 복원하며, no-delta task는 permanent Context를 유지하는가?

## Setup

같은 Desktop Workspace에서 isolated한 네 개의 새 Codex task를 순서대로 실행했다.

1. Decision `PURPLE_ORCHARD_AT_09`, TODO `PREPARE_GREEN_PACKET`, Due `2026-07-18` 확정
2. 이전 논의를 이어 현재 결정과 TODO 요청
3. `고마워.`
4. 현재 결정과 TODO를 다시 요청

## Expected

사용자 재설명 없이 현재 결정과 TODO가 복원되고 Event·Delta·State link가 유효하다.

## Result

Pass.

- Task 1 Stop hook이 pending capture를 만들었다.
- Task 2가 이전 turn view를 적용해 Event 1, Delta 1과 State 1을 만들고 세 marker를 즉시 복원했다.
- Task 3은 permanent Context를 바꾸지 않았다.
- Task 4는 task 3 capture를 No Delta로 처리하고 State만 읽어 세 marker를 복원했다.
- Task 4 command trace는 Delta나 Event를 읽지 않았다.

## Evidence

- Command: `python3 tests/run_phase3_codex_continuity.py`
- `PASS task 1 exact Stop-hook inbox capture`
- `PASS task 2 Event → Delta → State apply and immediate continuity`
- `PASS task 3 No Delta leaves permanent Context unchanged`
- `PASS task 4 State-first restore without Delta or Event read`
- Installed validator pass와 marker-owned artifact cleanup

## Decision

Phase 3 exit criteria를 충족한다. 한 turn 늦게 이전 capture를 분류하는 inbox flow로 hook의 source-only 책임과 Interface Codex의 의미 판단을 분리하면서 새 작업 continuity를 제공할 수 있다.
