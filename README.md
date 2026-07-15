# Podo

Podo는 Codex를 인터페이스로 사용하는 개인 비서다. 대화의 원본과 실제 변화를 분리해 보존하고, 새 작업에서도 현재 결정과 TODO를 이어갈 수 있게 만드는 것을 목표로 한다.

```text
Event → Delta → State
```

- Event: 무엇이 들어오거나 발생했는지에 대한 원본과 출처
- Delta: 그 Event로 인해 실제로 달라진 내용
- State: 지금 유효한 Context, 결정과 날짜가 있는 TODO

## Development Status

Podo는 아직 개발 중이며 실제 사용자 설치용 release가 없다. 현재 저장소에는 제품 구조, 정책, 데이터 템플릿과 local 개발 설치기가 있다. 실제 개인 데이터나 중요한 transcript를 넣지 않는다.

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

현재 `capture_event`는 입력을 검증한 뒤 명시적으로 실패하는 guard다. 실제 capture 기능이 아니므로 installer와 CLI도 capture 상태를 `guard-not-ready`로 표시한다.

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
```

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
