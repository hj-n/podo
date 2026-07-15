# Experiment 05 — Repeatability and Cleanup Gate

## Question

Everyday, recovery와 product journey가 이전 run의 상태에 의존하지 않고 각각 새 Workspace에서 같은 evidence shape로 반복되며, 성공과 실패 모두 temporary artifact를 정리하는가?

## Setup

- `python3 tests/run_phase8_suite.py`
- 세 journey를 `repeat-1`, `repeat-2` run ID로 순차 실행
- Temporary root의 `podo-phase8-{journey}-*` artifact를 실행 전후 비교
- 별도 subprocess에서 everyday journey를 `after-personalize` 지점에 test-only failure injection

## Result

Passed on 2026-07-15.

- Everyday journey: 두 run 모두 8개 stable step 통과
- Recovery journey: 두 run 모두 6개 stable step 통과
- Product journey: 두 run 모두 7개 stable step 통과
- 각 journey의 두 run은 step ID와 outcome 순서가 같았다.
- 시각과 생성 경로를 포함할 수 있는 evidence 문자열은 repeatability identity로 사용하지 않았다.
- 여섯 success run 뒤 새 temporary artifact가 남지 않았다.
- Controlled failure는 non-zero로 종료되고 마지막 `journey-failure` step과 `status: failed`를 포함한 schema 1 summary를 출력했다.
- Controlled failure 뒤에도 새 temporary Workspace가 남지 않았다.

## Evidence

- `tests/run_phase8_suite.py`
- `PHASE8_SUITE_SUMMARY`: phase 8, schema 1, repeats 2, status passed, controlled failure cleanup passed

## Decision

`python3 tests/run_phase8_suite.py`를 Phase 8 canonical synthetic command로 채택한다. Stable identity는 step ID와 outcome이며 State hash나 timestamp처럼 콘텐츠 정확성 검증에는 유용하지만 run마다 달라질 수 있는 값은 suite identity에서 제외한다.
