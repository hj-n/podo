# Phase 5 Gate Decision

- Decision: GO
- Decided: 2026-07-15
- Evidence: `experiments/`, `findings.md`, Phase 1–5 full regression

## Reason

Context apply와 request-based resolution은 staged Event, Delta, State와 receipt를 검증한 journaled transaction으로 처리한다. 모든 commit 경계의 강제 중단은 unfinished evidence를 남겼고 State는 기존 또는 검증된 새 version 중 하나로만 유지됐다. 비중첩 concurrent State 변화는 strict 3-way merge 후 검증됐고, 겹치는 변화는 현재 State를 보존하며 manual recovery로 분류됐다.

Doctor는 healthy, interrupted, link/original/lifecycle과 product drift를 사용자 파일 수정 없이 구분했다. Recovery plan은 evidence, target과 cleanup source의 hash/type/mode를 고정하며, exact plan ID와 재검증 없이는 적용되지 않는다. Stale plan, overlapping conflict와 manual plan은 변경 전에 중단했고, 성공한 plan의 재실행은 idempotent했다.

실제 Codex task에서는 baseline 생성, Delta 뒤 강제 중단, 다음 task의 자동 read-only 진단, 승인 전 State 무변경, exact plan 승인 적용과 State-first continuity를 재현했다. 최종 gate에서 Phase 1 계약, Phase 2 설치·실제 Codex, Phase 3 capture/context/실제 continuity, Phase 4 판단·TODO·실제 Codex 및 Phase 5 전체 suite를 다시 실행했다. 모든 marker-owned Desktop artifact는 제거됐다.

## Conditions

- `podo doctor`는 진단만 하며 Context나 recovery plan을 쓰지 않는다.
- `podo recover` plan 생성은 `.podo-work/recovery-plans/`만 쓸 수 있고, apply는 사용자가 확인한 exact plan ID가 필요하다.
- Missing original, damaged State와 overlapping change의 의미를 자동 재구성하지 않는다.
- Inbox의 `recovery_diagnosis`는 unfinished transaction이 있을 때 같은 read-only doctor 엔진을 자동 실행한 결과다.
- Production-supported transcript runtime은 계속 `0.144.0-alpha.4` 하나다.
- 실제 개인 데이터, remote distribution, product update와 Workspace migration은 이번 gate의 evidence가 아니다.

## Next Phase

Phase 6 — GitHub Distribution and Product Updates.
