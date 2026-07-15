# Phase 2 — Local Installation and Development Loop

## Goal

GitHub 배포 전에 현재 `realpodo/product/`를 원본으로 사용하여, 저장소 밖의 User Workspace를 한 명령으로 안전하게 설치하고 반복 검증할 수 있게 한다.

핵심은 파일 복사가 아니라 다음 세 가지다.

1. 제품 파일과 사용자 파일의 소유권을 지킨다.
2. 설치 중 실패해도 기존 Workspace를 훼손하지 않는다.
3. Codex policy와 hook 상태를 설치 성공과 capture 성공으로 혼동하지 않는다.

## Desktop Test Boundary

모든 Phase 2 end-to-end 테스트는 다음 전용 parent 아래에서만 실행한다.

```text
/Users/hj/Desktop/realpodo/                 Development Workspace
/Users/hj/Desktop/podo-test-workspaces/     Disposable test parent
└── <run-id>-<scenario>/                    Synthetic User Workspace
```

안전 규칙:

- 실제 개인 데이터나 기존 User Workspace를 사용하지 않는다.
- 각 생성 directory에 Phase 2 test marker를 기록한다.
- cleanup은 resolved path가 전용 parent의 직접 자식이고 marker가 현재 test suite와 일치할 때만 수행한다.
- 알 수 없는 파일이나 marker가 없는 directory는 삭제하지 않고 실패한다.
- 모든 검증 후 test child를 제거하고 parent가 비어 있을 때만 parent도 제거한다.

## Scope

Phase 2에서 한다:

- local product source를 사용하는 installer
- fresh, pre-populated와 same-version Workspace 설치
- product collision, symlink와 incompatible Workspace 차단
- create-once 사용자 파일 보존
- staging, failure injection과 rollback
- `.podo/bin/podo`의 `version`, `validate`, `hook-status`
- installed product manifest와 hash 검증
- hook review 안내와 synthetic Codex task acceptance
- Desktop test Workspace 생성과 안전한 cleanup

Phase 2에서 하지 않는다:

- GitHub 다운로드, Release와 checksum 배포
- 다른 제품 버전으로 update 또는 rollback
- 사용자 데이터 migration
- 실제 transcript capture와 Event writer
- Context transaction, doctor와 recover

## Installation State Contract

| Target state | Result |
|---|---|
| Missing or empty directory | Install |
| Existing user-owned files only | Preserve and create missing files |
| Same verified Podo version | Idempotent no-op for unchanged product files |
| Different or modified product-owned file | Stop with product collision |
| Incompatible `WORKSPACE_VERSION` | Stop without migration |
| Symlink at a managed path | Stop before writing |
| Partial or unverified Podo installation | Stop and report, do not guess |

## Meaningful Units

1. Phase 2 execution and safety contract
2. Installed product CLI and local installer
3. Preservation, collision and rollback suite
4. Desktop Codex and hook acceptance
5. Gate, cleanup and handoff

각 단위는 관련 검증을 통과한 뒤 commit하고 push한다.

## Steps

### 2.1 Phase 2 실행 계약

Plan, experiment, findings와 decision 구조를 만들고 Desktop test boundary와 cleanup 규칙을 고정한다.

Pass 조건: 모든 installer 결과와 test directory의 소유·삭제 조건이 문서화된다.

### 2.2 설치 모드 validator

Phase 1 validator를 다음 모드로 분리한다.

- installed-empty: Context가 비어 있어도 정상
- context-present: 존재하는 Context만 전체 검사
- synthetic-fixture: 최소 Event → Delta → State chain 요구

Pass 조건: fresh install은 통과하고 존재하는 손상 데이터는 모드와 무관하게 실패한다.

### 2.3 Self-contained Product CLI

설치된 `.podo/bin/podo`에 다음 명령을 만든다.

```text
podo version
podo validate
podo hook-status
```

Pass 조건: Development Workspace의 `tools/` 없이 임의의 cwd에서 Workspace root와 version을 찾고, capture guard를 ready로 표시하지 않는다.

### 2.4 Local installer

`tools/install_local.py --workspace <path>`를 구현한다. `AGENTS.podo.md`는 `AGENTS.md`로 변환하고 `.codex/`, `.podo/`를 설치한다.

Pass 조건: target path가 없어도 한 명령으로 Architecture와 일치하는 Workspace가 생성된다.

### 2.5 Staging과 preflight

제품을 temporary staging에 복사해 검증한 뒤 target의 symlink, collision, version과 file type을 모두 확인한다. Preflight가 끝나기 전 target을 바꾸지 않는다.

Pass 조건: preflight 실패 전후 target tree hash가 동일하다.

### 2.6 Create-once 사용자 데이터

Workspace version, user config, work·backup·Context directory는 없을 때만 만든다. 기존 값은 invalid해 보여도 덮어쓰지 않고 validation error로 보고한다.

Pass 조건: existing user-owned file의 byte hash와 permission이 설치 전후 동일하다.

### 2.7 Product manifest와 same-version reinstall

설치 source, product version과 product-owned file hash를 manifest에 기록한다. 같은 버전의 unchanged product는 검증 후 no-op으로 처리한다.

Pass 조건: 두 번째 실행이 product·user tree를 변경하지 않고 이미 설치된 상태를 명확히 보고한다.

### 2.8 Hook onboarding

Installer와 `podo hook-status`는 installed, trust-unverified와 capture-guard 상태를 구분한다. 사용자의 hook review·trust를 자동 승인하거나 우회하지 않는다.

Pass 조건: hook 파일 존재만으로 capture-ready를 출력하지 않는다.

### 2.9 Collision과 symlink 검증

다른 AGENTS, 수정된 hook·product, incompatible Workspace, file/directory type mismatch와 managed path symlink를 각각 검증한다.

Pass 조건: 각 case가 안정적인 error code로 실패하며 기존 byte hash가 유지된다.

### 2.10 Failure injection과 rollback

Staging 후, product apply 중, user initialization 중과 final validation 전에 실패를 주입한다. Installer가 이번 실행에서 만든 경로만 역순으로 제거한다.

Pass 조건: 기존 target은 보존되고 fresh target은 설치 전 상태로 돌아간다. 알 수 없는 파일은 삭제하지 않는다.

### 2.11 Desktop Codex acceptance

Desktop test parent에 실제 synthetic Workspace를 설치하고 새 Codex CLI task에서 다음을 검증한다.

- Interface `AGENTS.md`와 user config 적용
- State-first reading
- installed `.podo/bin/podo` 실행
- trusted test automation에서 `Stop` hook guard 호출
- `PODO_CAPTURE_NOT_IMPLEMENTED`와 Context hash 유지

Pass 조건: policy와 hook invocation은 확인되지만 capture success로 보고되지 않는다.

### 2.12 Gate와 cleanup

README에 실제 local development command만 추가하고, 전체 suite를 Desktop parent에서 실행한 뒤 marker가 있는 test child와 빈 parent를 정리한다.

Pass 조건:

- fresh, existing와 idempotent install 통과
- collision, symlink와 injected failure 통과
- user-owned bytes와 permissions 보존
- 새 Codex task와 hook guard acceptance 통과
- test parent가 없거나 실행 전 존재했던 unknown content만 그대로 남음
- Phase 3가 실제 capture를 구현할 수 있는 installed product loop 완성

## Outputs

```text
dev_docs/impl/phase_2/
├── plan.md
├── experiments/
│   ├── 01-install-contract.md
│   ├── 02-fresh-idempotent.md
│   ├── 03-existing-collisions.md
│   ├── 04-failure-rollback.md
│   ├── 05-cli-hook.md
│   └── 06-desktop-acceptance.md
├── findings.md
└── decision.md
```

## Exit Criteria

한 명령으로 Desktop의 깨끗한 임시 Podo Workspace를 설치하고 별도의 Codex 작업에서 열 수 있다. 반복 설치와 주요 실패에서도 사용자 소유 파일을 보존하며, 테스트가 만든 Workspace는 검증 후 안전하게 제거된다.
