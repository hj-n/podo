# Experiment 06 — Real Codex Capture

## Question

Desktop의 새 Codex task가 installed Stop hook을 통해 정확한 pending capture를 만드는가?

## Setup

Desktop marker-owned Workspace에 product `0.2.0`을 설치하고 isolated `CODEX_HOME`에서 bundled `codex-cli 0.144.0-alpha.4`의 새 작업을 실행했다. Exact hook definition을 확인한 vetted automation에서만 trust bypass를 사용했다.

## Expected

Runtime, session, turn과 transcript hash가 검증된 inbox capture가 한 개 생성된다.

## Result

Pass. Stop hook이 runtime, session과 turn을 검증한 pending capture 하나를 만들었고 hook health가 `ready`가 됐다. Codex 작업 중 permanent Context hash는 동일했다.

## Evidence

- Command: `python3 tests/run_phase2_codex_acceptance.py`
- Interface answer: user config name, State marker와 `VERSION=0.2.0`
- Hook: `capture-ready`
- Cleanup: Workspace, isolated Codex home과 empty test parent 제거

## Decision

현재 runtime에서 project-local `hooks.json`만으로 exact Stop source를 capture할 수 있다. Installer는 trust를 자동 승인하지 않고 CLI health는 실제 성공 receipt가 있기 전 `not-diagnosed`로 유지한다.
