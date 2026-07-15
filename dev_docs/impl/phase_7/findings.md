# Phase 7 Findings

Phase 7 실험 결과와 migration limitation을 기록한다.

## Confirmed

- Product version과 Workspace version은 별개이며 0.6.0 candidate infrastructure 자체는 Workspace 1과 호환될 수 있다.
- Normal update, migration apply와 full rollback은 서로 다른 approval boundary가 필요하다.
- `WORKSPACE_VERSION`은 migration descriptor의 일반 영향 path가 아니라 engine이 마지막에 적용하는 implicit transaction path다.
- 실제 Workspace 2 형식을 만들지 않고도 descriptor, plan, backup과 failure contract를 검증할 수 있다.
- Release selection, external/internal metadata, checksum and safe extraction are shared with the Phase 6 downloader rather than reimplemented for migrations.
- Identical current evidence and target identity produce one idempotent plan ID; planning writes only `.podo-work/migration-plans/`.
- A package that supports the current Workspace is a normal update, while a migration package needs one unique forward graph and exact affected paths.
