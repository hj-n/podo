# Podo

Podo는 Codex를 인터페이스로 사용하는 개인 비서다. 대화의 원본과 실제 변화를 분리해 보존하고, 새 작업에서도 현재 결정과 TODO를 이어갈 수 있게 만드는 것을 목표로 한다.

```text
Event → Delta → State
```

- Event: 무엇이 들어오거나 발생했는지에 대한 원본과 출처
- Delta: 그 Event로 인해 실제로 달라진 내용
- State: 지금 유효한 Context, 결정과 날짜가 있는 TODO

## Development Status

Podo는 아직 개발 중이며 실제 사용자 설치용 release가 없다. 현재 저장소에는 local 개발 설치기, `Event → Delta → State` core loop, deferred confirmation·TODO lifecycle과 중단된 Context transaction의 진단·승인 기반 복구가 있다. 실제 개인 데이터나 중요한 transcript를 넣지 않는다.

## Product and User Data

| Product-owned | User-owned |
|---|---|
| `AGENTS.md` | `WORKSPACE_VERSION` |
| `.codex/hooks.json` | `user_config.md` |
| `.podo/` | `events/`, `deltas/`, `state/` |
|  | `.podo-work/`, `.podo-backups/` |

일반 제품 update는 사용자 소유 파일을 덮어쓰지 않는다.

## Project Hook and Privacy

Podo는 Codex turn이 끝날 때 `Stop` hook으로 session ID, turn ID와 local transcript 경로를 capture entrypoint에 전달하도록 설계됐다.

- Hook은 사용자가 Workspace와 정확한 정의를 검토하고 신뢰한 뒤에만 실행한다.
- Hook은 별도 daemon이나 background monitor를 만들지 않는다.
- Transcript를 외부로 자동 전송하지 않는다.
- Raw Event에는 대화, 첨부 자료의 참조, command와 tool 결과처럼 민감할 수 있는 내용이 포함될 수 있다.
- Capture source나 completeness를 검증하지 못하면 Delta와 State를 갱신하지 않는다.

현재 `capture_event`는 `codex-cli 0.144.0-alpha.4`의 local transcript를 versioned adapter로 검증해 `.podo-work/inbox/`에 임시 capture한다. Hook은 Context 의미를 판단하거나 State를 직접 수정하지 않는다.

다음 Interface 작업은 이전 turn의 review view를 확인한다.

- 미래 Context에 영향을 주는 명확한 변화면 immutable Event, Delta와 State로 적용한다.
- 변화가 없으면 Event를 만들지 않고 `no-delta` receipt만 남긴다.
- 불확실하거나 기존 결정과 충돌하면 State를 유지하고 한 번만 defer해 확인한다.
- 후속 확인이나 기각은 원래 보류된 원본과 연결한다.

지원하지 않는 runtime, session·turn identity mismatch, 손상된 원본이나 partial capture는 Delta와 State를 갱신하지 않는다.

## Local Development Installation

GitHub release가 나오기 전에는 이 저장소의 `product/`를 사용해 저장소 밖의 synthetic 또는 disposable Workspace에만 설치한다.

```bash
python3 tools/install_local.py --workspace /absolute/path/to/podo-workspace
```

Installer는 제품 파일을 설치하고 사용자 소유 파일은 없을 때만 만든다. 기존 제품 파일이 다르거나 Workspace version이 호환되지 않거나 managed path가 symlink면 쓰기 전에 중단한다. 설치 후에는 Codex에서 Workspace와 `.codex/hooks.json`을 직접 검토하고 신뢰해야 하며, installer가 이 단계를 자동 승인하지 않는다.

설치된 Workspace에서는 어느 directory에서든 다음 명령을 실행할 수 있다.

```bash
/absolute/path/to/podo-workspace/.podo/bin/podo version
/absolute/path/to/podo-workspace/.podo/bin/podo validate
/absolute/path/to/podo-workspace/.podo/bin/podo hook-status
/absolute/path/to/podo-workspace/.podo/bin/podo inbox --json
/absolute/path/to/podo-workspace/.podo/bin/podo doctor --json
/absolute/path/to/podo-workspace/.podo/bin/podo recover --json
/absolute/path/to/podo-workspace/.podo/bin/podo recover --apply <plan-id> --json
```

`doctor`는 파일을 바꾸지 않고 unfinished transaction, Context link·hash, capture lifecycle, product manifest와 hook health를 진단한다. `recover`는 `.podo-work/recovery-plans/`에 영향 범위와 현재 hash가 고정된 계획만 만들며, Context는 사용자가 확인한 exact plan ID를 `--apply`로 전달할 때만 변경한다. 계획 이후 관련 파일이 달라졌거나 State 변경이 겹치면 적용하지 않는다.

이 명령은 local development용이다. 아직 `curl` 기반 GitHub 설치나 update 명령은 제공하지 않는다.

## Development Validation

전체 Phase 1 계약 검증:

```bash
python3 tests/run_phase1_contracts.py
```

합성 User Workspace를 직접 조립하고 검사하려면:

```bash
workspace="$(mktemp -d /tmp/podo-phase1.XXXXXX)"
python3 tools/build_synthetic_workspace.py --output "$workspace"
python3 tools/validate_workspace.py "$workspace"
```

두 명령은 실제 개인 데이터 대신 고정된 synthetic fixture만 사용한다.

Phase 2 installer의 fresh, existing, collision과 rollback을 Desktop의 marker-owned synthetic Workspace에서 검증하려면:

```bash
python3 tests/run_phase2_installation.py
```

Suite는 `/Users/hj/Desktop/podo-test-workspaces/` 아래에서 자신이 만든 marker가 있는 directory만 정리하고, parent는 비어 있을 때만 제거한다.

Phase 3 core loop 전체 검증:

```bash
python3 tests/run_phase3_capture.py
python3 tests/run_phase3_context.py
python3 tests/run_phase3_codex_continuity.py
```

마지막 command는 Desktop에 marker-owned Workspace와 isolated `CODEX_HOME`을 만들고 네 개의 실제 Codex 작업으로 capture, apply, No Delta와 State-first restore를 검증한 뒤 모두 정리한다.

Phase 4 판단 lifecycle과 TODO 검증:

```bash
python3 tests/run_phase4_decisions.py
python3 tests/run_phase4_todo.py
python3 tests/run_phase4_codex_acceptance.py
```

마지막 command는 Desktop의 marker-owned Workspace에서 실제 새 Codex 작업들을 이어 decision, defer, confirmation, TODO 위치·완료, credential 제외와 State-first 복원을 검증한 뒤 모두 정리한다.

Phase 5 transaction, 동시성, 읽기 전용 진단과 승인 복구 검증:

```bash
python3 tests/run_phase5_suite.py
python3 tests/run_phase5_codex_acceptance.py
```

첫 command는 임시 synthetic Workspace에서 모든 commit 경계, 비중첩/중첩 State 변경, doctor의 무변경 보장, stale plan 거부와 두 receipt 사이의 복구를 검증한다. 마지막 command는 Desktop의 marker-owned Workspace와 실제 새 Codex 작업으로 승인 전 무변경과 승인 후 복구를 검증한다.

## Repository Map

```text
product/    배포될 Podo 제품의 원본
tools/      합성 Workspace 조립과 검증 도구
tests/      정상·손상 fixture 계약 테스트
dev_docs/   Philosophy, Architecture와 구현 기록
```

- [Initial Philosophy](dev_docs/initial_philosophy.md)
- [Initial Architecture](dev_docs/initial_architecture.md)
- [Implementation Roadmap](dev_docs/impl/implementation_roadmap.md)
- [Current Status](dev_docs/impl/status.md)
