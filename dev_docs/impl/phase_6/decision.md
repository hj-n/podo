# Phase 6 Gate Decision

- Decision: GO
- Decided: 2026-07-15
- Evidence: `experiments/`, `findings.md`, Phase 1–6 full regression and public v0.5.3 Release

## Reason

Release builder는 제품만 포함하는 archive, checksum, metadata와 bootstrap을 재현 가능하게 만든다. Standalone installer와 product update는 checksum·identity·safe archive·Workspace compatibility를 쓰기 전에 검사하고, `AGENTS.md`, `.codex`, `.podo`를 하나의 transaction으로 교체한다. 모든 handled failure boundary에서 이전 제품이 복원됐고 사용자 소유 파일의 content와 mode는 유지됐다.

Public GitHub에서 v0.5.2를 인증 없이 설치한 뒤 latest v0.5.3으로 update하고 exact v0.5.2로 rollback하는 흐름이 통과했다. 실제 Codex는 일반 version 확인에서는 update하지 않았고, 명시적 요청에서만 canonical command를 실행했으며, 다음 새 task가 v0.5.3에서 정상 시작했다.

최종 gate에서 Phase 1–6 synthetic와 실제 Codex 회귀가 통과했다. v0.5.3 tag rebuild는 공개 archive와 byte-identical했고 GitHub latest asset, source commit, SHA-256, syntax, Git integrity와 Desktop cleanup을 다시 확인했다.

## Conditions

- 일반 product update는 Workspace migration 승인이 아니다. 호환되지 않는 Workspace는 쓰기 전에 중단하며 Phase 7에서 별도 plan·backup·rollback을 구현한다.
- 사용자 소유 영역은 계속 일반 update target이 아니다.
- 직접 수정된 제품, unfinished Context/product transaction, checksum·identity·origin 불일치를 자동으로 우회하지 않는다.
- 성공 후 새 Codex task를 시작하고 변경된 hook을 다시 검토한다.
- v0.5.0과 v0.5.1의 historical downloader limitation은 immutable Release에 남아 있다. 기본 설치와 update는 latest v0.5.3을 사용한다.
- 독립 package signing, automatic background update, Windows native support와 지원 transcript runtime 확대는 이번 Phase의 결과로 주장하지 않는다.

## Next Phase

Phase 7 — Workspace Migrations and Full Rollback. 실제 Workspace format을 임의로 바꾸지 않고 synthetic Workspace 1→2 fixture로 migration plan, 별도 승인, 사용자 데이터 backup, failure rollback과 backup retention부터 설계한다.
