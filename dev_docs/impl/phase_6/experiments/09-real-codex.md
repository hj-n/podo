# Experiment 09 — Real Codex Product Manager Acceptance

## Question

실제 Codex가 명시적 요청에만 update하고 새 task 안내와 사용자 파일 보존을 유지하는가?

## Status

Passed on 2026-07-15.

## Setup

- public v0.5.2를 marker-owned disposable Desktop Workspace에 설치했다.
- 실제 bundled Codex CLI를 isolated `CODEX_HOME`과 synthetic user config로 세 번 실행했다.
- 첫 task는 version 확인만 요청하고 update를 명시적으로 금지했다.
- 둘째 task는 latest update를 명시적으로 요청했다.
- 셋째 task는 새 task startup과 설치 version 확인만 요청했다.

## Result

- 첫 task는 v0.5.2를 보고했고 command trace에 `podo update`가 없었다.
- 둘째 task는 `.podo/bin/podo update` canonical command를 실행해 v0.5.3을 설치하고 새 task와 hook 재검토를 안내했다.
- 셋째 task는 추가 update 없이 startup policy를 수행하고 v0.5.3을 보고했다.
- 세 task 전체에서 synthetic user sentinel의 hash와 mode가 유지됐다.
- 설치된 Workspace validation과 marker 기반 Desktop cleanup이 통과했다.

## Evidence

- `python3 tests/run_phase6_codex_acceptance.py`
- response markers: `NO_UPDATE_CHECK`, `NEW_TASK_REQUIRED`, `POST_UPDATE_STARTUP_OK`
- command execution trace와 `.podo/VERSION`을 응답과 별도로 검사했다.

## Decision

제품 update는 Interface Codex의 일반 startup 행동이 아니라 사용자의 명시적 외부 action으로 유지한다. 성공 후 새 task에서 새 Operating Policy를 읽는 경계를 유지한다.
