# Phase 9 Gate Decision

- Decision: GO — unpublished 0.7.0 candidate
- Updated: 2026-07-20

## Evidence

- 현재 runtime capture와 unknown-runtime fail-closed 경계가 통과했다.
- TODO·중복·plain/broken reference 진단은 읽기 전용이며 관련 파일 hash를 바꾸지 않았다.
- Event chunk manifest는 legacy original과 동일한 SHA-256으로 복원되고, backup·별도 rollback plan·주입 실패 복원이 통과했다.
- Workspace 1→2 migration은 People과 Research만 additive하게 추가하고 기존 State bytes를 보존했다.
- People과 Research의 별도 저장, PDF 정본·hash 중복 감지, paper/topic/project transaction과 TODO의 State 정본 경계가 통과했다.
- 실제 Codex 6-task acceptance와 Phase 1–9 전체 synthetic regression이 통과했다.
- 실제 legacy engine을 재현한 0.6.0 → compatible bridge → 0.7.0 migration regression이 통과했고, 기존 plain reference는 경고로 보존하면서 새 plain reference는 apply 전에 거부했다.
- 테스트에는 synthetic 자료만 사용했고 disposable Desktop Workspace는 정리되었다.

## Release Boundary

이 결정은 현재 checkout의 제품 candidate가 Phase 9 gate를 통과했다는 뜻이다. 사용자가 별도로 승인한 하나의 외부 Workspace migration은 완료됐지만, Public tag와 GitHub Release 승인은 포함하지 않는다.
