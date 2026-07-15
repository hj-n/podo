# Experiment 08 — Phase 7 Final Gate

## Question

Phase 7 migration·backup·full rollback이 이전 Phase의 설치, Context, 판단, recovery와 공개 배포 경계를 깨지 않고 Phase 8로 진행할 수 있는가?

## Setup

- Current development product: unpublished 0.6.0 candidate, Workspace 1 compatible.
- Synthetic target products provided Workspace 2/3 and test-only migration entrypoints.
- Marker-owned Desktop Workspaces and isolated `CODEX_HOME` were used for real Codex acceptance.
- Public latest v0.5.3 distribution remained separate from the candidate.

## Result

Passed on 2026-07-15.

### Phase regression

- Phase 1 contracts and corruption cases: passed.
- Phase 2 install/failure rollback and real Codex policy/hook on product 0.6.0: passed.
- Phase 3 capture, Context suite and four-task real Codex continuity: passed.
- Phase 4 decisions/TODO suites and 15-task real Codex acceptance: passed on a clean retry after one network-unreachable Codex call.
- Phase 5 transaction/concurrency/doctor/recovery suite and real Codex approved recovery: passed.
- Phase 6 package/update/bootstrap suite, anonymous public round trip and real Codex explicit-only update: passed.
- Phase 7 five-program synthetic suite and six-task real Codex migration approval acceptance: passed.

### Migration evidence

- Unique 1→2 and 1→2→3 chains applied only after exact plan approval.
- Stale product/user evidence, invalid/ambiguous graph, failing entrypoint and undeclared user changes failed before current data apply.
- Nine migration and nine full-rollback failure boundaries restored exact start snapshots.
- Original migration backup and rollback-start safety backup remained after success and handled failure.
- Normal update did not create migration approval artifacts.
- Doctor/startup exposed unfinished migration and blocked another product update.
- A cross-process lock returned `E_MIGRATION_BUSY` before backup or Workspace change.

### Candidate and static gate

- Source commit `4151171bc6ddb0c0531ab69e528a201a9ae036ad` produced two byte-identical 0.6.0 candidate archives.
- Candidate SHA-256: `024e21364bf2248af1620647175d0462287a3e2566c349feab42d6dd5be5c772`.
- Candidate metadata declared only Workspace 1 and archive inspection found no real `1-to-2` migration or user Context.
- 42 Python files, 13 JSON files and tracked shell scripts passed syntax checks.
- Git object integrity and `git diff --check` passed.
- Public latest remained v0.5.3 with four expected assets; v0.6.0 was not published.
- Desktop test children and Phase 6/7 temporary artifacts were cleaned.

## Decision

Phase 7 exit criteria are met for migration infrastructure using synthetic Workspace formats. Actual Workspace format 2 adoption and public candidate publication remain separate product/release decisions.
