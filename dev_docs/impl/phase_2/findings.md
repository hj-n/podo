# Phase 2 Findings

## Confirmed

- Product validator를 `.podo/scripts/`에 포함하면 설치된 Workspace가 Development Workspace 없이 자체 검증할 수 있다.
- Manifest와 actual product hash·mode를 함께 확인해야 수정된 product와 idempotent reinstall을 구분할 수 있다.
- Create-once 설치는 기존 user-owned byte와 permission을 그대로 보존할 수 있다.
- Staging 뒤 쓰기 전 preflight하고 created-path journal을 역순으로 정리하면 주요 설치 실패를 원상 복구할 수 있다.
- Hook installed, trust와 capture readiness는 서로 다른 상태다.

## Limitations

- Local installer만 구현됐다. GitHub Release 다운로드, update, 다른 version 교체와 migration은 아직 없다.
- Capture entrypoint는 의도적으로 실패하는 guard다.
- 실제 새 Codex task의 project policy와 Stop hook acceptance는 Experiment 06에서 확인해야 한다.

## Phase 3 Handoff

Installed CLI와 local Workspace loop가 capture 구현을 받을 준비가 됐다. Phase 3는 guard를 versioned transcript adapter와 immutable Event writer로 교체하되 installer의 manifest·ownership 경계를 유지해야 한다.
