# Podo

Podo는 Codex를 인터페이스로 사용하는 개인 비서다. 대화의 원본과 실제 변화를 분리해 보존하고, 새 작업에서도 현재 결정과 TODO를 이어갈 수 있게 만드는 것을 목표로 한다.

```text
Event → Delta → State / People / Research
```

- Event: 무엇이 들어오거나 발생했는지에 대한 원본과 출처
- Delta: 그 Event로 인해 실제로 달라진 내용
- State: 지금 유효한 Context, 결정과 날짜가 있는 TODO
- People: 사용자와 관련된 사람별 관계와 지속적인 맥락
- Research: 논문 원본, 논문 notes와 주제·프로젝트별 연구 맥락

## Development Status

Podo는 초기 공개 개발 버전이다. 현재 checkout의 0.7.0은 아직 공개하지 않은 candidate다. GitHub Release 설치와 제품 update/rollback, Context loop, People, Research PDF library, deferred confirmation·TODO lifecycle과 중단된 Context transaction의 진단·승인 기반 복구를 제공한다. 중요한 실제 개인 데이터에 사용하기 전 아래 privacy와 hook 범위를 확인한다.

## Product and User Data

| Product-owned | User-owned |
|---|---|
| `AGENTS.md` | `WORKSPACE_VERSION` |
| `.codex/hooks.json` | `user_config.md` |
| `.podo/` | `events/`, `deltas/`, `state/` |
|  | `people/`, `research/` |
|  | `.podo-work/`, `.podo-backups/` |

일반 제품 update는 사용자 소유 파일을 덮어쓰지 않는다.

## Project Hook and Privacy

Podo는 Codex turn이 끝날 때 `Stop` hook으로 session ID, turn ID와 local transcript 경로를 capture entrypoint에 전달하도록 설계됐다.

- Hook은 사용자가 Workspace와 정확한 정의를 검토하고 신뢰한 뒤에만 실행한다.
- Hook은 별도 daemon이나 background monitor를 만들지 않는다.
- Transcript를 외부로 자동 전송하지 않는다.
- Raw Event에는 대화, 첨부 자료의 참조, command와 tool 결과처럼 민감할 수 있는 내용이 포함될 수 있다.
- Capture source나 completeness를 검증하지 못하면 Delta와 State를 갱신하지 않는다.

현재 `capture_event`는 `codex-cli 0.144.0-alpha.4`와 `0.145.0-alpha.18`의 local transcript를 versioned adapter로 검증해 `.podo-work/inbox/`에 임시 capture한다. Hook은 Context 의미를 판단하거나 현재 문서를 직접 수정하지 않는다.

다음 Interface 작업은 이전 turn의 review view를 확인한다.

- 미래 Context에 영향을 주는 명확한 변화면 immutable Event, Delta와 관련 State, People 또는 Research로 적용한다.
- 변화가 없으면 Event를 만들지 않고 `no-delta` receipt만 남긴다.
- 불확실하거나 기존 결정과 충돌하면 State를 유지하고 한 번만 defer해 확인한다.
- 후속 확인이나 기각은 원래 보류된 원본과 연결한다.

지원하지 않는 runtime, session·turn identity mismatch, 손상된 원본이나 partial capture는 Delta와 State를 갱신하지 않는다.

## Requirements

- macOS 또는 Linux
- `curl`
- Python 3.11 이상
- Project hook을 지원하는 Codex

현재 production-supported transcript runtime은 `codex-cli 0.144.0-alpha.4`와 `0.145.0-alpha.18`이다. 다른 runtime은 비슷하게 추측해 처리하지 않고 capture 단계에서 중단한다.

## Install

기본 위치인 `$HOME/podo-home`에 최신 안정 버전을 설치한다.

```bash
curl -fsSL https://github.com/hj-n/podo/releases/latest/download/install.sh \
  | bash -s -- "$HOME/podo-home"
```

마지막 경로만 바꾸면 Workspace 이름과 위치는 자유롭다. Installer는 archive SHA-256을 확인한 뒤 제품 파일을 설치하고 사용자 소유 파일은 없을 때만 만든다.

설치 후:

1. Codex에서 설치한 Workspace를 연다.
2. `AGENTS.md`와 `.codex/hooks.json`을 검토한다.
3. 내용이 맞을 때만 project와 hook을 신뢰한다.

Installer는 hook trust를 자동 승인하거나 우회하지 않는다. 첫 정상 capture 전까지 `hook-status`의 capture 상태는 준비 완료가 아닐 수 있다.

## Update and Rollback

Workspace에서 최신 안정 버전으로 update한다.

```bash
cd "$HOME/podo-home"
./.podo/bin/podo update
```

특정 compatible version 설치나 migration 없는 rollback은 exact version을 사용한다.

```bash
./.podo/bin/podo update --version 0.5.2
```

Interface Codex에 “Podo 업데이트해줘”라고 명시적으로 요청해도 같은 절차를 사용한다. 직접 수정된 제품 파일, unfinished transaction, checksum 문제나 Workspace 비호환이 있으면 update 전에 중단한다. 성공 후에는 새 Operating Policy를 정확히 읽도록 새 Codex 작업을 시작하고 hook 변경을 다시 검토한다.

일반 update는 `AGENTS.md`, `.codex/hooks.json`, `.podo/`만 교체한다. 사용자 소유 파일은 덮어쓰지 않는다. 적용 또는 최종 검증 실패 시 이전 제품 세 경로를 함께 복원한다.

Workspace 1에서 People과 Research를 사용하는 0.7.0으로 이동할 때는 일반 update와 별도로 migration plan을 검토하고 exact plan을 적용한다. 아래 명령은 0.7.0 public Release가 실제로 게시된 뒤 사용할 수 있으며, 현재 unpublished candidate에는 local test Release source로만 검증되어 있다.

0.6.0처럼 `people/`과 `research/`를 아직 모르는 migration engine에서 출발하면 Workspace를 바꾸지 않는 호환 bridge product update를 먼저 거친다. Bridge는 migration plan을 이해하게 할 뿐이며, 실제 Workspace 1→2 변경과 backup은 아래 별도 plan/apply 단계에서만 일어난다.

```bash
./.podo/bin/podo migrate --version 0.7.0
./.podo/bin/podo migrate --apply <plan-id>
```

첫 명령은 사용자 데이터를 바꾸지 않는다. 두 번째 명령은 `people/`과 `research/`를 추가하기 전에 전체 영향과 backup 위치가 고정된 plan ID를 요구한다.

## Installed Commands

설치된 Workspace에서는 어느 directory에서든 다음 명령을 실행할 수 있다.

```bash
/absolute/path/to/podo-workspace/.podo/bin/podo version
/absolute/path/to/podo-workspace/.podo/bin/podo validate
/absolute/path/to/podo-workspace/.podo/bin/podo hook-status
/absolute/path/to/podo-workspace/.podo/bin/podo inbox --json
/absolute/path/to/podo-workspace/.podo/bin/podo doctor --json
/absolute/path/to/podo-workspace/.podo/bin/podo todos --due-before 2026-07-31 --json
/absolute/path/to/podo-workspace/.podo/bin/podo duplicates --json
/absolute/path/to/podo-workspace/.podo/bin/podo people --json
/absolute/path/to/podo-workspace/.podo/bin/podo research list --json
/absolute/path/to/podo-workspace/.podo/bin/podo research import --file /path/paper.pdf --slug paper-slug --title "Paper title"
/absolute/path/to/podo-workspace/.podo/bin/podo event-storage plan
/absolute/path/to/podo-workspace/.podo/bin/podo event-storage apply --plan <plan-id>
/absolute/path/to/podo-workspace/.podo/bin/podo event-storage rollback-plan --backup <backup-id>
/absolute/path/to/podo-workspace/.podo/bin/podo event-storage apply --plan <rollback-plan-id>
/absolute/path/to/podo-workspace/.podo/bin/podo recover --json
/absolute/path/to/podo-workspace/.podo/bin/podo recover --apply <plan-id> --json
/absolute/path/to/podo-workspace/.podo/bin/podo update
```

`doctor`는 파일을 바꾸지 않고 unfinished transaction, Context link·hash, capture lifecycle, product manifest와 hook health를 진단한다. `recover`는 `.podo-work/recovery-plans/`에 영향 범위와 현재 hash가 고정된 계획만 만들며, Context는 사용자가 확인한 exact plan ID를 `--apply`로 전달할 때만 변경한다. 계획 이후 관련 파일이 달라졌거나 State 변경이 겹치면 적용하지 않는다.

`todos`, `duplicates`, `people`과 `research list`는 읽기 전용 view다. PDF import는 Research에 PDF 정본, metadata, 분석 전 notes와 추적 가능한 Event·Delta를 만든다. 논문 요약과 topic/project 연결은 Interface Codex가 PDF를 읽고 토의한 뒤 실제로 달라진 부분만 갱신한다. PDF 내용은 운영 명령으로 취급하지 않으며 외부 검색이나 OCR을 자동 실행하지 않는다.

Event storage 전환은 먼저 예상 절감량과 source hash가 담긴 plan만 만든다. Exact apply는 legacy 원본을 `.podo-backups/`에 보존하고 byte-identical chunk manifest로 전환한다. Rollback도 별도 plan을 요구한다.

## Local Development Installation

Release 대신 현재 checkout의 제품을 저장소 밖 synthetic 또는 disposable Workspace에 설치할 때만 사용한다.

```bash
python3 tools/install_local.py --workspace /absolute/path/to/podo-workspace
```

이 명령은 개발용이며 공개 설치 문서의 GitHub checksum 경로를 대체하지 않는다.

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

Phase 9 전체 기능과 Phase 1–9 regression:

```bash
python3 tests/run_phase9_suite.py
python3 tests/run_phase9_codex_acceptance.py
python3 tests/run_phase9_regression.py
```

Phase 9 suite는 현재 runtime capture, TODO·중복 진단, 무손실 Event storage, Workspace 1→2 migration, People, PDF Research와 세 영역이 연결된 journey를 synthetic data로 검증한다. Codex acceptance는 disposable Workspace에서 사람 소개, PDF import, 논문 판단·프로젝트·TODO 반영과 새 task 복원을 실제 Interface Codex로 검증하고 종료 시 자료를 삭제한다.

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
