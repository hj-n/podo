# Experiment 01 — Product Structure and Policy

## Question

제품·사용자 소유권을 분리한 배포 원본과 작은 Interface policy router를 만들 수 있는가?

## Setup

Architecture의 product-owned 경계를 따라 `product/AGENTS.podo.md`, `.codex/hooks.json`과 `.podo/` 기본 구조를 만들었다. 제품·사용자 경로는 `ownership.json`에 별도로 기록했다.

제품용 `AGENTS.podo.md`를 저장소 밖의 synthetic Workspace에서 `AGENTS.md`로 변환하고, 합성 `user_config.md`와 State를 넣은 뒤 새로운 Codex CLI 작업을 실행했다. Prompt는 이전 결정과 TODO만 요청했다.

## Expected

`product/`가 Architecture와 일치하고 `AGENTS.podo.md`가 상세 정책을 중복하지 않는다.

## Result

Pass.

- `product/`에는 `AGENTS.md`가 없고 제품 정책 원본은 `AGENTS.podo.md`다.
- Router는 네 개의 상세 정책만 연결하고 세부 내용을 중복하지 않는다.
- 새 작업은 `user_config.md`, `context_restore.md`, 관련 State만 읽었다.
- 현재 결정과 Due가 있는 TODO를 정확히 복원했다.
- 작업 전후 합성 user config, policies와 State hash가 동일했다.

## Evidence

- Synthetic assistant name: `포도테스트`
- Restored decision: 금요일 오전 9시 합성 회의
- Restored TODO: 2026-07-17까지 초록색 문서 준비
- Trace read order: user config → context restore policy → State
- `git diff --check` and JSON parse checks passed.

## Decision

현재 `AGENTS.podo.md`를 작은 Interface router의 기준으로 사용한다. 상세 판단은 `.podo/policies/`에 유지하고, 제품 소유 경로는 `.podo/contracts/ownership.json`을 validator가 검사하도록 한다.
