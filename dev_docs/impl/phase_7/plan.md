# Phase 7 Plan — Workspace Migrations and Full Rollback

## Goal

사용자 데이터 형식이 바뀌는 Release를 일반 product update와 구분하고, 영향 설명과 exact approval 뒤에만 이전하며, 실패하거나 사용자가 되돌리기로 한 경우 이전 제품과 사용자 데이터를 함께 복원한다.

## Safety Invariants

1. 단순 `podo update` 요청은 Workspace migration 승인으로 해석하지 않는다.
2. Migration plan 생성은 permanent Context와 제품을 바꾸지 않는다.
3. Apply는 사용자가 확인한 exact plan ID를 요구한다.
4. Plan은 현재 제품 manifest, Workspace version, 영향받는 사용자 path의 hash/type/mode와 target Release identity를 고정한다.
5. Plan 이후 관련 파일이 달라지면 backup이나 apply 전에 중단한다.
6. Migration entrypoint는 verified target package 안에 있고 선언된 사용자 path만 바꿀 수 있다.
7. Backup은 제품 세 root, `WORKSPACE_VERSION`과 영향받는 사용자 path를 포함한다.
8. Backup은 `.podo-backups/`에 남기며 자동 삭제하거나 외부 전송하지 않는다.
9. 새 제품, migrated data와 `WORKSPACE_VERSION`은 하나의 journaled transaction으로 취급한다.
10. Handled failure와 final validation failure는 이전 제품과 사용자 데이터를 함께 복원한다.
11. 성공한 migration의 full rollback도 현재 데이터를 덮어쓰므로 별도 plan과 exact approval을 요구한다.
12. 복구 자체가 실패하면 추가 변경을 멈추고 journal과 backup 위치를 보존한다.

## User Flow

```text
podo migrate --version X.Y.Z
→ Release와 migration chain 검증
→ 변경 이유, exact 영향 path, backup 위치와 rollback 조건 표시
→ migration plan 생성

podo migrate --apply <plan-id>
→ plan stale 여부 재검증
→ target Release 재검증
→ 이전 제품과 사용자 데이터 backup
→ staged migration 실행과 allowlist 검사
→ 제품 + migrated data 적용
→ final validation 또는 전체 rollback
```

성공한 migration을 되돌릴 때는 다음처럼 두 단계로 진행한다.

```text
podo migrate rollback --backup <backup-id>
→ 현재 상태와 복원 영향을 고정한 rollback plan

podo migrate --apply <rollback-plan-id>
→ 현재 상태 safety backup
→ 이전 제품 + 사용자 데이터 복원
→ final validation 또는 rollback 시도 전 상태 복원
```

## Migration Package Contract

Target product는 필요한 migration을 다음 구조로 포함할 수 있다.

```text
.podo/migrations/
└── 1-to-2/
    ├── migration.json
    └── migrate.py
```

`migration.json`은 시작·목표 Workspace version, 사람이 이해할 설명, 추가·이동·제거되는 내용, exact 영향 path와 entrypoint를 선언한다. 여러 version을 건너뛰면 target package 안에서 연속된 유일한 chain을 찾아 순서대로 실행한다.

## Steps

### 7.1 Contracts and Failure Matrix

- migration descriptor, plan, journal, backup과 receipt 계약을 정의한다.
- plan, download, stale check, backup, staged migration, 제품·데이터 apply와 final validation 실패 지점을 목록화한다.

### 7.2 Migration Discovery and Impact Planning

- verified target package에서 migration graph를 읽는다.
- 현재 Workspace에서 target product가 지원하는 형식까지 유일한 chain을 찾는다.
- 설명, exact 영향 path, 추가·이동·제거 내용과 backup 위치를 plan으로 만든다.

### 7.3 Exact Approval and Stale Plan Protection

- plan ID에 source/target identity와 현재 file evidence를 포함한다.
- exact plan ID 없이 apply하지 않는다.
- plan 이후 제품이나 영향 path가 달라지면 중단한다.

### 7.4 Persistent Backup

- 이전 제품 세 root, install manifest, `WORKSPACE_VERSION`과 영향 path를 `.podo-backups/`에 기록한다.
- 존재하지 않았던 path도 absence로 기록해 rollback 때 새 파일을 제거할 수 있게 한다.
- backup manifest 자체의 hash/type/mode evidence를 검증한다.

### 7.5 Journaled Product-and-Data Apply

- target product와 migrated user data를 staging에서 먼저 검증한다.
- migration이 선언하지 않은 사용자 path를 바꾸면 중단한다.
- 각 apply 경계를 journal에 기록하고 handled failure에서 전체 restore한다.

### 7.6 Ordered Multi-hop Migration

- 1→2→3 같은 연속 chain을 순서대로 실행한다.
- missing, ambiguous, cyclic, wrong-start와 target-incompatible graph를 쓰기 전에 거부한다.

### 7.7 Explicit Full Rollback

- migration backup과 현재 receipt가 일치할 때 rollback plan을 만든다.
- 현재 상태 safety backup 뒤 이전 제품과 data를 함께 복원한다.
- rollback failure는 rollback 시작 전 상태로 복원한다.

### 7.8 CLI, Policy and Diagnosis

- `podo migrate --version`, `podo migrate --apply`, `podo migrate rollback --backup`을 제공한다.
- Interface policy에 일반 update와 migration approval을 분리한다.
- unfinished migration journal을 doctor와 startup diagnosis에 표시한다.

### 7.9 Synthetic Workspace 1→2 Suite

- 실제 제품의 Workspace 1 형식은 바꾸지 않는다.
- synthetic target product와 migration fixture로 plan → apply → full rollback을 검증한다.
- 사용자 파일 content/mode, backup retention과 모든 failure boundary를 검사한다.

### 7.10 Real Codex Approval Acceptance

- marker-owned Desktop Workspace에서 update 요청만으로 migration이 실행되지 않는지 확인한다.
- 영향 설명 뒤 exact approval을 받은 task만 apply하는지 검증한다.
- 새 task에서 migrated State를 읽고, full rollback도 별도 승인을 요구하는지 확인한다.

### 7.11 Gate and Phase 8 Handoff

- Phase 1–7 regression, syntax, cleanup과 backup evidence를 확인한다.
- limitation과 GO/NO-GO를 기록한다.
- 실제 Workspace format 2와 public Release는 별도 제품 결정 및 publish 승인 전에는 만들지 않는다.

## Meaningful Delivery Units

1. Phase 7 contract와 plan
2. migration discovery와 exact impact plan
3. persistent backup과 staged migration
4. journaled product-and-data apply/rollback
5. multi-hop과 full rollback
6. CLI, policy와 doctor integration
7. synthetic failure suite
8. real Codex approval acceptance
9. final gate와 Phase 8 handoff

각 단위는 관련 검증을 통과한 뒤 별도로 commit하고 push한다.

## Exit Criteria

- 단순 product update가 migration을 실행하거나 승인으로 간주하지 않는다.
- Synthetic Workspace 1→2 migration이 exact plan approval 뒤에만 실행된다.
- Plan은 변경 이유, 영향 path, backup 위치와 rollback 조건을 사람이 이해할 수 있게 보여준다.
- 성공 시 target product와 Workspace version이 함께 검증된다.
- 각 failure boundary에서 이전 제품과 사용자 데이터가 복원된다.
- 성공 후 backup이 보존되고, 별도 승인된 full rollback이 이전 제품과 data를 함께 복원한다.

## Non-Goals

- 실제 Workspace format 2 채택
- 실제 개인 Workspace migration
- 승인 없는 automatic migration 또는 backup deletion
- Remote backup, backup encryption 또는 cloud sync
- Public tag와 GitHub Release publish
