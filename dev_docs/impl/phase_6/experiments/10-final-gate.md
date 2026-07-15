# Experiment 10 — Phase 6 Final Gate

## Question

Phase 6의 공개 설치와 product update가 이전 Phase의 Context·판단·복구 불변식을 깨지 않고 재현 가능한 Release로 닫혔는가?

## Setup

- 현재 main과 public v0.5.3 Release를 검사했다.
- synthetic suite와 marker-owned Desktop Workspace만 사용했다.
- 실제 Codex acceptance는 isolated `CODEX_HOME`에서 실행했다.
- v0.5.3 tag를 detached temporary worktree에서 다시 build했다.

## Result

Passed on 2026-07-15.

### Phase regression

- Phase 1 contracts and nine corruption cases: passed.
- Phase 2 fresh/existing/idempotent install, failure rollback and real Codex policy/hook: passed.
- Phase 3 capture, Event → Delta → State, No Delta and four-task continuity: passed.
- Phase 4 decision/defer/confirmation/TODO suites and 15-task real Codex acceptance: passed on a clean retry after one Codex call timeout.
- Phase 5 transaction/concurrency/doctor/recovery suites and seven-task real Codex recovery acceptance: passed.
- Phase 6 deterministic package, install, update failure boundaries, downloader, bootstrap, public Release round trip and real Codex product manager acceptance: passed.

Phase 3의 첫 gate 실행은 두 번째 task의 요청이 pending 적용을 명시하지 않아 marker만 답하고 permanent Context를 만들지 않았다. Acceptance prompt를 startup policy의 적용 책임이 명확하도록 좁히고 실패 시 command/message/inbox evidence를 남기게 한 뒤 전체 네 task가 통과했다. 제품 데이터 손상은 없었다.

### Release and static gate

- v0.5.3 tag `0f9f19d62fac7443bfa3fdbf272960b0a1c0e00a` rebuild와 public archive가 byte-identical했다.
- archive SHA-256은 `6292aadd2f8d34ce232e7fea0d6007f4b73c445bd1948096dfea65756cbcfe06`이다.
- GitHub latest는 non-draft, non-prerelease v0.5.3과 네 expected asset을 반환했다.
- 34 Python files, 12 JSON files와 tracked shell scripts의 syntax가 통과했다.
- Git object integrity, `git diff --check`, clean worktree와 temporary worktree cleanup이 통과했다.
- `/Users/hj/Desktop/podo-test-workspaces` 아래 test child와 Phase 6 `/tmp` artifact가 남지 않았다.

## Evidence

- `python3 tests/run_phase1_contracts.py`
- `python3 tests/run_phase2_installation.py`
- `python3 tests/run_phase2_codex_acceptance.py`
- `python3 tests/run_phase3_context.py`
- `python3 tests/run_phase3_capture.py`
- `python3 tests/run_phase3_codex_continuity.py`
- `python3 tests/run_phase4_decisions.py`
- `python3 tests/run_phase4_todo.py`
- `python3 tests/run_phase4_codex_acceptance.py`
- `python3 tests/run_phase5_suite.py`
- `python3 tests/run_phase5_codex_acceptance.py`
- `python3 tests/run_phase6_suite.py`
- `python3 tests/run_phase6_public_update.py`
- `python3 tests/run_phase6_codex_acceptance.py`

## Decision

Phase 6 exit criteria are met. Workspace format changes, migration approval, user-data backup and product-plus-data full rollback move to Phase 7.
