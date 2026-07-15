# Phase 6 Plan — GitHub Distribution and Product Updates

## Goal

README의 검증된 명령으로 새 User Workspace에 Podo를 설치하고, 사용자 소유 파일을 그대로 보존하면서 최신 또는 특정 제품 버전으로 update와 rollback할 수 있게 한다.

## Safety Invariants

1. Release package에는 제품 원본과 installer만 포함하고 사용자 Context를 포함하지 않는다.
2. Archive는 SHA-256 검증 전 추출하거나 실행하지 않는다.
3. Archive path traversal, absolute path와 symlink를 거부한다.
4. Install과 update는 staging 전체를 검증한 뒤 제품 소유 영역만 교체한다.
5. `AGENTS.md`, `.codex/hooks.json`, `.podo/`는 하나의 제품 transaction으로 취급한다.
6. `WORKSPACE_VERSION`, `.podo-work/`, `.podo-backups/`, `user_config.md`, `events/`, `deltas/`, `state/`는 일반 update target이 아니다.
7. 현재 product manifest와 실제 제품 파일이 다르면 update 전에 중단한다.
8. Target product가 현재 Workspace version을 지원하지 않으면 migration으로 확대하지 않고 중단한다.
9. 적용 또는 최종 validation 실패 시 이전 제품 세 경로를 함께 복원한다.
10. Rollback은 migration이 없고 target product가 현재 Workspace version을 지원할 때만 일반 update와 같은 절차로 수행한다.
11. Operating Policy나 hook이 바뀔 수 있으므로 성공 후 새 Codex task와 hook 재검토를 안내한다.
12. Repository visibility는 배포 구현과 별도 결정이다. Phase 6가 private repository를 public으로 바꾸지 않는다.

## Distribution Contract

각 GitHub Release는 다음 asset을 제공한다.

```text
podo-<version>.tar.gz
podo-<version>.tar.gz.sha256
install.sh
release.json
```

- Archive: `product/`, standalone `install.py`와 내부 `release.json`
- Checksum: archive filename과 exact SHA-256
- `release.json`: product version, supported Workspace versions, archive/checksum asset, source commit과 release notes
- `install.sh`: 해당 Release version을 기본값으로 설치하는 작은 bootstrap

Release asset과 extracted product의 version, manifest와 checksum이 모두 일치해야 한다.

## Product Update Transaction

```text
release 조회와 notes 확인
→ archive/checksum download
→ checksum과 safe archive 검증
→ 새 제품 staging 및 Workspace compatibility 확인
→ 현재 manifest/제품 drift 확인
→ 이전 제품 backup
→ AGENTS.md → .codex → .podo 교체
→ 새 제품 전체 validation
→ success receipt 또는 세 제품 경로 rollback
```

진행 evidence는 `.podo-work/product-updates/<update-id>/`에 journal로 남긴다. 성공 시 큰 staged/backup 자료는 정리하고 작은 receipt만 남긴다. 실패 후 rollback까지 성공하면 현재 제품은 기존 manifest와 정확히 일치해야 한다.

## Repository Visibility Boundary

현재 `hj-n/podo`는 private repository다. Phase 6는 visibility를 변경하지 않는다.

- Private 상태: GitHub 인증 token 또는 authenticated `gh`로 Release asset을 받는다.
- Public 전환 이후: 같은 `install.sh`와 update downloader가 token 없이 동작한다.
- README는 현재 실제로 작동하는 private 설치 명령과 향후 public에서 사용할 짧은 명령을 명확히 구분한다.

## Steps

### 6.1 Contracts and Failure Matrix

- package, release metadata, installed manifest와 product update journal 계약을 정의한다.
- fresh install, update, downgrade/rollback과 migration-required를 구분한다.
- download, checksum, staging, 각 제품 경로 교체와 final validation 실패 지점을 목록화한다.

### 6.2 Deterministic Release Builder

- `tools/build_release.py`로 versioned archive, checksum, release metadata와 bootstrap을 만든다.
- 같은 source commit의 두 build가 byte-identical한지 검증한다.
- 제품 이외 파일, pycache, local manifest, credential과 사용자 Context가 없는지 검사한다.

### 6.3 Shared Product Installer

- extracted package의 standalone installer와 local development installer가 같은 core apply 계약을 사용한다.
- 빈 외부 Workspace install, 기존 사용자 파일 보존과 idempotency를 유지한다.
- installed manifest에 release source, commit, archive checksum과 제품 파일 hash를 기록한다.

### 6.4 Journaled Product Update and Rollback

- 제품 세 경로의 staged replacement와 rollback을 구현한다.
- 직접 수정, partial product, symlink, incompatible Workspace와 unfinished Context recovery 상태에서 fail closed한다.
- 각 apply 경계 failure injection에서 이전 제품과 사용자 파일 hash 보존을 검증한다.

### 6.5 Release Downloader and CLI

- public/authorized GitHub API에서 latest 또는 exact tag의 assets와 notes를 읽는다.
- `podo update [--version X.Y.Z]`를 제공한다.
- 테스트 전용 local Release source는 명시적 test guard 아래에서만 연다.

### 6.6 Bootstrap Installer and README

- `install.sh`가 checksum을 검증한 뒤 standalone installer를 실행하게 한다.
- README에 prerequisites, private/public 설치, Workspace 열기, hook trust, update, rollback, doctor/recover와 소유권 경계를 간결히 기록한다.

### 6.7 Synthetic Distribution Suite

- 두 synthetic product version으로 fresh install → update → rollback을 반복한다.
- 사용자 소유 파일 content/mode, direct modification, checksum damage, unsafe archive, incompatible version과 모든 update failure boundary를 검증한다.

### 6.8 First GitHub Release

- version/tag/release notes와 asset을 일치시킨다.
- GitHub에서 다시 내려받아 local build checksum과 비교한다.
- private repository에서는 authenticated end-to-end install을 검증한다.

### 6.9 Second Version Update and Rollback

- 다음 compatible version을 Release한다.
- 실제 GitHub assets로 첫 version 설치 → latest update → exact previous version rollback을 검증한다.
- update 후 새 Codex task와 hook 재검토 안내를 확인한다.

### 6.10 Real Codex Product Manager Acceptance

- marker-owned Desktop Workspace에서 Interface Codex가 명시적 update 요청에만 정해진 command를 사용하게 한다.
- update 전 사용자 files, update 후 version, 새-task 안내와 다음 task의 정상 startup을 검증한다.

### 6.11 Gate and Phase 7 Handoff

- Phase 1–6 전체 suite, JSON/shell/Python syntax, package reproducibility, Git tags/assets와 Desktop cleanup을 확인한다.
- evidence, limitation과 GO/NO-GO를 기록한다.
- migration이 필요한 update는 구현하지 않고 Phase 7 handoff로 남긴다.

## Meaningful Delivery Units

1. Phase 6 contract와 plan
2. deterministic release builder
3. shared installer와 fresh package install
4. journaled update/rollback
5. GitHub downloader와 CLI
6. bootstrap과 README
7. synthetic distribution gate
8. first GitHub Release
9. second Release update/rollback
10. real Codex acceptance
11. final gate와 Phase 7 handoff

각 단위는 관련 검증을 통과한 뒤 별도로 commit하고 push한다.

## Exit Criteria

- README의 현재 repository visibility에 맞는 한 명령으로 빈 외부 Workspace에 설치할 수 있다.
- Latest와 exact version asset의 checksum과 source identity가 설치 manifest에 남는다.
- 사용자 파일 content/mode를 유지하며 compatible version update와 rollback을 완료한다.
- 직접 수정, checksum 불일치, unsafe archive, incompatible Workspace와 각 중간 실패가 기존 제품을 보존한다.
- 실제 GitHub에서 다시 받은 assets로 install → update → rollback이 통과한다.
- 실제 Codex update 요청 후 새 task 안내와 다음 task의 정상 Podo startup이 확인된다.

## Non-Goals

- GitHub repository visibility 변경
- Workspace migration과 사용자 data backup restore
- Automatic background update
- Package signing infrastructure beyond GitHub HTTPS, release identity and published SHA-256
- Windows native support

