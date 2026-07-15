# Experiment 04 — Validator and Fixtures

## Question

정상 synthetic Workspace와 주요 손상을 dependency 없이 일관되게 판정할 수 있는가?

## Setup

표준 Python library만 사용하는 두 개발 도구를 만들었다.

- `tools/build_synthetic_workspace.py`: product tree와 template을 disposable Workspace에 조립
- `tools/validate_workspace.py`: checked-in contract에 따라 Workspace 검증

`tests/fixtures/phase1_cases.json`은 유효한 합성 Workspace에 한 가지 손상만 주입하는 8개 case와 기대 error code를 정의한다. `tests/run_phase1_contracts.py`가 두 번의 deterministic build, 정상 validation과 모든 failure case를 실행한다.

## Expected

정상 fixture는 통과하고 손상 fixture는 고유한 code와 이해 가능한 이유로 실패한다.

## Result

Pass.

두 개의 독립된 temporary Workspace가 동일한 digest로 생성됐고 모두 validation을 통과했다. 8개 손상 fixture는 성공한 척하지 않고 각각 기대한 code로 실패했다.

검증 범위는 required paths, ownership, product·Workspace version compatibility, hook shape, user config, Event timestamps·completeness·original·hash, Delta links, State links, TODO dates와 unresolved template token이다.

## Evidence

- `PASS missing-original -> E_EVENT_ORIGINAL`
- `PASS event-hash-mismatch -> E_EVENT_HASH`
- `PASS unknown-completeness -> E_EVENT_COMPLETENESS`
- `PASS broken-delta-link -> E_DELTA_LINK`
- `PASS todo-missing-created -> E_TODO_CREATED`
- `PASS checked-todo-missing-completed -> E_TODO_COMPLETED`
- `PASS unresolved-template-token -> E_TEMPLATE_TOKEN`
- `PASS incompatible-workspace-version -> E_VERSION_COMPATIBILITY`
- First deterministic digest: `1cdb24e1849ec06502b381d243eb236a831f25c83f622737377f1397a2ca2b61`

## Decision

합성 fixture 원본을 완성된 User Workspace 형태로 commit하지 않는다. Builder가 매번 저장소 밖에 생성하고, fixture manifest는 손상 의도와 기대 code만 보관한다. 이 validator를 Phase 2 installer와 이후 doctor 검증의 초기 기준으로 사용한다.
