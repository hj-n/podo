# Experiment 02 — Migration Failure Matrix

## Question

어느 단계에서 실패해도 승인 전 무변경 또는 이전 제품·사용자 데이터 전체 복원으로 귀결되는가?

## Matrix

| Boundary | Expected result |
|---|---|
| Release download, checksum, identity, graph validation | Plan 없음, Workspace 무변경 |
| Plan 생성 뒤 영향 path 변경 | Backup 전 stale plan 거부 |
| Backup 중 실패 | Apply 없음, 불완전 backup 표시 |
| Staged migration entrypoint 실패 | 제품·사용자 데이터 apply 없음, backup 보존 |
| 선언되지 않은 path 변경 | Apply 전 거부, backup 보존 |
| Product root apply 중 실패 | 이전 product와 user data 복원 |
| Migrated user path apply 중 실패 | 이전 product와 user data 복원 |
| `WORKSPACE_VERSION` 또는 final validation 실패 | 이전 product와 user data 복원 |
| Full rollback apply 실패 | Rollback 시작 전 product와 user data 복원 |
| Restore 자체 실패 | 추가 변경 중단, journal과 backup 보존 |

## Status

Apply and full rollback boundaries passed on 2026-07-15.

`after-backup`, transaction preparation, each of the three product roots, affected user path, `WORKSPACE_VERSION`, before/after final validation failures all preserved the exact previous product and selected user file hash/mode. Complete backups remained and handled transaction directories were cleaned.

The equivalent separately approved full rollback boundaries preserved the exact rollback-start product and user snapshot using the retained safety backup.
