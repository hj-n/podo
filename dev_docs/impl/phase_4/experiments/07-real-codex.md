# Experiment 07 — Real Codex Acceptance

## Question

실제 새 Codex task들에서도 같은 판단 정책과 cross-task continuity가 재현되는가?

## Status

Passed.

## Setup

- Desktop의 marker-owned Workspace, isolated `CODEX_HOME`과 external sentinel을 만들었다.
- local product 0.3.0을 설치하고 trusted project에서 실제 새 Codex task 15개를 순서대로 실행했다.
- 실제 credential, 개인 자료와 외부 시스템은 사용하지 않았다.
- hook trust 우회 flag는 이 저장소가 정의를 직접 통제하는 acceptance automation에서만 사용했다.

## Scenarios and Result

1. `user_config.md`의 이름·성격·response style marker가 첫 답변에 적용됐다.
2. 명확한 Alpha 결정은 추가 확인 없이 Event·Delta·State로 반영됐다.
3. 기존 결정과 충돌하는 미확정 내용은 State를 덮어쓰지 않았다.
4. 사용자가 다음 task에도 이어 달라고 명시한 unresolved conflict는 한 번 defer됐고 무관한 요청에서 질문을 반복하지 않았다.
5. 후속 confirmation은 exact capture가 생긴 다음 task에서 적용됐다.
6. resolution Event는 confirmation original과 deferred related original을 함께 보존했다.
7. 별도 Alpha/Beta State가 만들어졌고 위치가 불명확한 자연어 TODO는 조기 추가되지 않았다.
8. 사용자가 Alpha를 선택하자 TODO에 Created와 Due가 기록되고 Beta에는 들어가지 않았다.
9. 완료 요청은 Completed 날짜와 Result를 기록했다.
10. synthetic credential capture는 영구 Context에서 제외되고 receipt만 남았다.
11. 실행 요청이 아닌 external sentinel write는 수행되지 않았다.
12. 마지막 task는 State를 읽고 Alpha 결정과 완료 TODO를 복원했으며 Delta와 Event를 읽지 않았다.
13. Workspace validation이 통과했고 세 Desktop child는 marker 확인 후 제거됐다.

## Evidence

```text
python3 tests/run_phase4_codex_acceptance.py
PASS task 1 user configuration and clear-decision capture
PASS task 2 clear decision applied without reconfirmation
PASS task 3 ambiguous conflict does not overwrite current State
PASS task 4 conflict deferred once and unrelated task did not repeat it
PASS task 5 confirmation captured without bypassing evidence
PASS task 6 confirmed conflict resolution with related original
PASS tasks 7-8 separate State and ambiguous natural-language TODO
PASS tasks 9-10 TODO location resolved with Created and Due
PASS tasks 11-12 TODO completion date and result
PASS tasks 13-14 credential exclusion and external no-op boundary
PASS task 15 State-first continuity without Event or Delta read
PASS Phase 4 Desktop Codex artifacts cleaned
```

## Finding

“좋을지도 모른다”처럼 채택되지 않은 아이디어는 No Delta가 맞고, 미래에 다시 확인할 unresolved Context인지 모델만으로 항상 같은 경계 판단을 기대하기 어렵다. 사용자가 다음 task에 보존해 달라고 명시한 경우는 defer로 처리한다는 규칙을 policy에 추가했다. 실제 acceptance는 이 명확한 사용자 의도를 검증한다.

## Decision

Phase 4 실제 Codex gate 시나리오는 통과했다. 최종 전체 regression과 cleanup을 실행해 GO/NO-GO를 판정한다.
