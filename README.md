# Podo

Podo는 Codex를 인터페이스로 사용하는 개인 비서다. 대화의 원본과 실제 변화를 분리해 보존하고, 새 작업에서도 현재 결정과 TODO를 이어갈 수 있게 만드는 것을 목표로 한다.

```text
Event → Delta → State
```

- Event: 무엇이 들어오거나 발생했는지에 대한 원본과 출처
- Delta: 그 Event로 인해 실제로 달라진 내용
- State: 지금 유효한 Context, 결정과 날짜가 있는 TODO

## Development Status

Podo는 아직 개발 중이며 실제 사용자 설치용 release가 없다. 현재 저장소에는 제품 구조, 정책, 데이터 템플릿과 synthetic Workspace validator가 있다. 실제 개인 데이터나 중요한 transcript를 넣지 않는다.

설치·update 명령은 Phase 2 이후 실제 artifact와 검증이 준비됐을 때 제공한다.

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

현재 `capture_event`는 입력을 검증한 뒤 명시적으로 실패하는 Phase 1 guard다. 실제 capture 기능이 아니며 설치용으로 공개하지 않는다.

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
