# Experiment 02 — Fresh and Idempotent Installation

## Question

한 명령으로 fresh Workspace를 만들고 같은 version을 재실행해 no-op으로 유지할 수 있는가?

## Setup

Desktop의 absent child path에 local installer를 실행했다. 첫 설치 뒤 marker를 추가하고 전체 tree의 file hash, mode, directory와 symlink 상태를 snapshot한 다음 같은 명령을 다시 실행했다.

## Expected

첫 실행은 완전한 Workspace를 만들고 두 번째 실행은 모든 hash와 permission을 유지한다.

## Result

Pass. 첫 실행은 `INSTALLED`, 두 번째 실행은 `ALREADY_INSTALLED`를 반환했다. 두 번째 실행 전후 tree snapshot은 동일했다.

## Evidence

- Installed product: `AGENTS.md`, `.codex/`, `.podo/`
- Create-once data: `WORKSPACE_VERSION`, `user_config.md`, `.podo-work/`, `.podo-backups/`, `events/`, `deltas/`, `state/`
- Installed validation: `OK mode=context-present`

## Decision

같은 version이라는 문자열만 보지 않고 manifest와 실제 product file을 모두 확인한 경우에만 idempotent reinstall로 처리한다.
