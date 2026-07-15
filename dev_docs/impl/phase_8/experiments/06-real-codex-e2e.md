# Experiment 06 — Real Codex End-to-End Journey

## Question

실제 Codex의 서로 다른 task들이 하나의 User Workspace에서 개인화, Context 판단, recovery와 product delivery 경계를 잃지 않고 처음부터 끝까지 이어지는가?

## Setup

- Marker-owned Desktop container 아래 Workspace, isolated `CODEX_HOME`, synthetic Release store
- Product 0.8.0 / Workspace 1에서 시작
- Compatible product 0.9.0과 synthetic Workspace 1→2 target 1.0.0
- 실제 Codex CLI 16개 새 task, Stop hook과 canonical Podo CLI 사용
- 사용자 데이터는 고정 acceptance marker만 포함
- `python3 tests/run_phase8_codex_acceptance.py`

## Result

Passed on 2026-07-15.

### Context and judgment

- Tasks 1–2: user configuration을 적용하고 결정/TODO capture를 traceable Context로 승격했다.
- Task 3: No Delta 대화가 permanent Context를 바꾸지 않았다.
- Tasks 4–7: 기존 결정과 충돌하는 미확정 제안을 한 번만 보류하고, 후속 확인에서 결정을 바꾸며 TODO를 완료했다.
- 응답 marker뿐 아니라 State bytes, Event/Delta links, inbox/deferred lifecycle과 validator로 결과를 확인했다.

### Recovery

- Test-only failure로 Context transaction을 Delta boundary 뒤에 중단했다.
- Task 8은 startup의 `PODO_D001_TRANSACTION_INCOMPLETE` diagnosis만 설명하고 apply하지 않았다.
- Task 9는 명시적 승인 뒤 recovery plan과 exact plan ID를 사용해 transaction을 완료했다.
- Recovery 뒤 State가 target marker를 포함하고 unfinished transaction이 사라졌으며 validator가 통과했다.

### Product lifecycle

- Task 10: product 0.8.0→0.9.0 compatible update가 user bytes와 mode를 보존했다.
- Task 11: 1.0.0 normal update는 incompatibility에서 멈추고 migration plan/backup을 만들지 않았다.
- Tasks 12–13: migration impact review는 non-applying이었고 exact apply만 product 1.0.0 / Workspace 2를 설치했다.
- Tasks 14–15: full rollback review는 safety backup을 만들지 않았고 exact apply가 product 0.9.0 / Workspace 1과 pre-migration user evidence를 복원했다.
- Task 16: 새 task가 restored State와 TODO를 State-first로 읽었고 추가 product/data apply를 실행하지 않았다.

### Cleanup

- Final summary: schema 1, phase 8, 16 tasks, 9 stable integrated steps, status passed.
- Desktop container는 exact parent와 marker를 확인한 뒤 제거됐다.
- Isolated Codex home, transcripts, synthetic packages와 Releases가 남지 않았다.

## Harness Corrections

최종 성공 전에 세 가지 assertion 문제를 발견했다. 모두 marker 검증 뒤 fixture가 정리됐고 제품 코드는 바꾸지 않았다.

- 실제 State의 inline Delta 표현을 가정한 recovery request 조립을 별도 `Recovery Evidence` token으로 바꿨다.
- Non-zero product update command도 command trace에 포함하도록 parser를 고쳤다.
- 자연어 응답의 `Format: 2` 문장 부호 대신 marker, version과 plan evidence를 검사했다.

## Evidence

- `tests/run_phase8_codex_acceptance.py`
- `PHASE8_CODEX_SUMMARY`: `personalized-context`, `no-delta`, `conflict-todo`, `approved-recovery`, `compatible-update`, `update-migration-boundary`, `migration-review-apply`, `full-rollback`, `post-rollback-state-first`

## Decision

실제 Codex 통합 흐름은 Phase 8 exit evidence로 채택한다. 응답 문구는 사용자에게 이해하기 쉬운 범위에서 자유롭게 두고, acceptance는 marker 외에도 command, plan, version, hash, journal과 backup으로 판정한다.
