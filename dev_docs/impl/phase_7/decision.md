# Phase 7 Gate Decision

- Decision: GO
- Decided: 2026-07-15
- Evidence: `experiments/`, `findings.md`, Phase 1–7 full regression and unpublished 0.6.0 candidate

## Reason

Verified target package의 migration graph는 시작·목표 Workspace version, 사람이 이해할 설명, ordered changes, exact 영향 path와 entrypoint hash를 plan에 고정한다. 일반 update는 호환되지 않는 Workspace에서 중단하며 migration plan이나 backup을 만들지 않는다. Plan review와 exact apply는 별도 동작이고, stale product/user evidence나 target identity 변화는 backup 전에 거부된다.

Apply는 이전 제품 세 root, `WORKSPACE_VERSION`과 영향 user data를 `.podo-backups/`에 보존한 뒤 complete staging에서 migration을 실행한다. 선언 밖 user/product 변화는 current Workspace 적용 전에 중단한다. 제품, migrated data와 Workspace version은 journaled transaction으로 적용되고, 모든 handled failure boundary에서 이전 snapshot이 복원됐다.

성공한 migration의 full rollback도 별도 plan과 exact approval을 요구한다. Plan은 migration 이후 변경된 영향 path를 보여주며, apply는 rollback-start safety backup을 만든 뒤 이전 제품과 data를 함께 복원한다. 실제 Codex 여섯 task에서 update-only, migration review/apply, rollback review/apply와 두 new-task 경계가 모두 재현됐다.

최종 gate에서 Phase 1–7 synthetic 및 실제 Codex 회귀, public v0.5.3 분리, 0.6.0 candidate reproducibility, syntax, Git integrity와 cleanup이 통과했다.

## Conditions

- 실제 Workspace 2 형식과 production migration은 별도 제품 결정 전에는 추가하지 않는다.
- 일반 update 요청을 migration 또는 full rollback 승인으로 해석하지 않는다.
- Backup과 journal을 사용자 승인 없이 삭제하지 않는다.
- Interrupted migration은 doctor evidence를 보존하고 update를 중단한다. 의미나 filesystem 상태를 추측해 자동 복원하지 않는다.
- Verified migration entrypoint의 OS-level sandboxing, encrypted/remote backup, Windows support와 automatic backup retention은 이번 결과로 주장하지 않는다.
- Public v0.6.0 tag/Release는 별도 publish 승인과 release candidate 재검증 전에는 만들지 않는다.

## Next Phase

Phase 8 — Integration and End-to-End Validation. 설치, 개인화, Context continuity, 판단, recovery, product update, migration 성공·실패와 full rollback을 하나의 반복 가능한 통합 흐름으로 묶고 실제 사용자 데이터 없이 전체 시나리오를 검증한다.
