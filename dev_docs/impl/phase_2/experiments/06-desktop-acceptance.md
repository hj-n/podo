# Experiment 06 — Desktop Workspace Acceptance and Cleanup

## Question

Desktop 외부 Workspace의 새 Codex task에서 policy와 hook guard가 적용되고 test artifact가 안전하게 정리되는가?

## Setup

Local installer로 `/Users/hj/Desktop/podo-test-workspaces/`의 marker-owned child에 Podo를 설치했다. 별도 marker-owned `CODEX_HOME`은 기존 auth file만 symlink하고 project trust만 설정했다. Workspace는 synthetic assistant name과 State decision을 가졌고 git repository로 초기화했다.

Bundled `codex-cli 0.144.0-alpha.4`에서 새 `codex exec --json` 작업을 `workspace-write` sandbox와 `never` approval로 실행했다. Test automation은 설치된 hook command가 정확한지 먼저 확인한 뒤 stderr만 `.podo-work/phase2-stop.stderr`로 redirect하여 guard 호출을 계측했고, vetted hook에 한해 `--dangerously-bypass-hook-trust`를 사용했다.

## Expected

Synthetic policy와 CLI는 동작하고 hook guard는 명시적으로 실패하며 Context hash가 유지된다. Marker가 있는 test Workspace만 제거된다.

## Result

Pass.

- Interface Codex가 user config의 이름, State의 현재 결정과 설치된 CLI version을 정확히 반환했다.
- `Stop` hook이 실제 `capture_event` guard를 호출했고 `PODO_CAPTURE_NOT_IMPLEMENTED`를 남겼다.
- User Context hash는 작업 전후 동일했다.
- Empty `.codex/config.toml` 유무를 분리 실험했고, 파일 없이 설치된 `.codex/hooks.json`만으로 hook이 호출됐다.
- Workspace와 isolated Codex home은 marker 검증 뒤 제거됐고 빈 Desktop test parent도 제거됐다.

## Evidence

- Command: `python3 tests/run_phase2_codex_acceptance.py`
- Codex result: `NAME=합성포도;DECISION=DESKTOP_PHASE2_OK;VERSION=0.1.0`
- Guard result: `PODO_CAPTURE_NOT_IMPLEMENTED`
- Context result: `Context hashes unchanged`
- Cleanup result: `Desktop Codex acceptance artifacts cleaned`
- Official behavior: project hook은 trusted `.codex/` layer에서만 load되고 exact definition review가 필요하다. Vetted automation의 일회성 bypass만 허용된다.

## Decision

Phase 2 acceptance에 충분하다. Policy, State-first restore, installed CLI와 hook invocation을 실제 새 Codex 작업에서 확인했다. 현재 guard의 exit `78` stderr는 Codex JSON event stream에 직접 노출되지 않으므로 acceptance test만 redirect로 계측한다. 실제 capture와 사용자에게 보이는 health signal은 Phase 3에서 supported Stop hook output contract와 함께 구현한다.
