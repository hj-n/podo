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
- Exact plan approval is represented by supplying the full plan ID; version-only apply is not available.
- Running migration code on a full staged Workspace allows final target validation and declared-change comparison before current product or user files are replaced.
- Persistent backup can be complete even when staged migration later fails; retaining it makes the failure recoverable without treating a retry as new approval.
- Applying `WORKSPACE_VERSION` last gives final validation one clear product/data compatibility point, while handled failures still restore all roots from backup.
- Strictly increasing descriptor versions make graph traversal finite; more than one reachable chain is rejected as ambiguous.
- Full rollback may intentionally overwrite post-migration user changes, so the plan names changed affected paths and apply retains a separate rollback-start safety backup.
- Neither the original migration backup nor the rollback safety backup is automatically deleted after success or handled failure.
- Normal product update remains fail-closed for incompatible Workspace versions and cannot create or apply migration approval artifacts.
- Context, product-update and migration recovery requirements need separate startup fields because their safe recovery procedures differ.
- A filesystem lock serializes migration/full-rollback apply in the supported macOS/Linux environment without treating a leftover lock file as an unfinished transaction.
- Across six real Codex tasks, natural-language requests preserved all four approval boundaries: update-only, migration review/apply, and full rollback review/apply.
- Response wording is not sufficient acceptance evidence; command traces, installed versions, plan/backup timing and State hashes independently confirmed behavior.
- A new task after product/data replacement reads the installed policy and current State without repeating migration or rollback.

## Known Limitations

- Product 0.6.0 is an unpublished development candidate. Public installs still receive v0.5.3.
- No real Workspace format 2 or production migration descriptor has been adopted; all 1→2/3 evidence is synthetic.
- Migration entrypoints come from a checksum-verified target package and run against staging, but they are not isolated by a separate OS sandbox. Undeclared staged user changes and product changes are detected before apply; arbitrary external side effects are outside this engine's guarantee.
- A hard process kill can leave a migration journal and partially applied filesystem state. Doctor/startup diagnose and block further update, but automatic interrupted-migration recovery is not claimed.
- Backups may duplicate sensitive Event data. They remain local and are not automatically deleted, encrypted or uploaded.
- Full rollback currently requires the installed product to remain the exact committed migration target; a later product update must be resolved before using that backup.
- Apply serialization uses `flock`, matching the current macOS/Linux support boundary; Windows native support is not claimed.
