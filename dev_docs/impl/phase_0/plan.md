# Phase 0 — Core Feasibility Plan

## Goal

Podo 전체를 구현하기 전에 다음 핵심 전제가 현재 Codex 환경에서 실제로 성립하는지 확인한다.

1. User Workspace의 작은 `AGENTS.md`가 Interface Codex의 역할을 안정적으로 만든다.
2. 필요한 상세 정책과 사용자 설정을 상황에 맞게 읽을 수 있다.
3. 대화 전체 원본과 출처를 자동으로 Event에 남길 수 있다.
4. 새 작업이 기존 State를 읽고 자연스럽게 이어진다.

Phase 0는 제품 구현 단계가 아니다. 합성 데이터와 저장소 밖의 disposable Workspace로 위험한 전제를 먼저 검증하는 단계다.

## Validation Environment

- Primary surface: macOS Codex desktop의 Local Project
- Repeatable test surface: 같은 Codex runtime을 사용하는 Codex CLI
- Development Workspace: 현재 `realpodo`
- User Workspace: 저장소 밖에 매번 새로 만드는 임시 디렉터리
- Data: 실제 개인 정보가 없는 synthetic conversation과 fixture만 사용
- Evidence: 원본 transcript는 임시 디렉터리에만 두고, 저장소에는 민감 정보가 없는 결과와 재현 절차만 기록

Desktop 전용 동작을 CLI 결과로 추정하지 않는다. 공통 runtime 동작은 CLI로 반복 검증하고, surface 차이는 별도로 명시한다.

## Meaningful Units

각 단위가 검증되면 관련 문서와 evidence를 함께 commit하고 push한다.

1. 계획과 실험 계약
2. Instruction·policy·config 검증
3. Transcript source와 Event capture 검증
4. 새 작업 연속성과 failure 검증
5. Findings와 gate decision

## Steps

### 0.1 Define the disposable environment

임시 User Workspace와 합성 입력을 반복해서 만들 수 있게 한다. 실행한 Codex 버전, surface, 경로와 시간을 evidence에 남긴다.

Pass 조건:

- 개발 저장소 밖에 깨끗한 Workspace를 만들 수 있다.
- 실제 사용자 파일이나 기존 Codex transcript를 읽지 않는다.
- 같은 절차를 다시 실행할 수 있다.

### 0.2 Validate `AGENTS.md` loading

작은 Interface `AGENTS.md`에 합성 marker와 역할 경계를 넣고 새로운 Codex 작업에서 확인한다. 파일 변경 전후와 새 작업에서의 차이를 비교한다.

Pass 조건:

- 새 작업이 별도 prompt 없이 marker와 역할을 따른다.
- Development Workspace의 지침과 섞이지 않는다.
- 실행 중 변경된 지침이 아니라 새 작업 시작 시 읽은 instruction chain을 기준으로 동작한다.

### 0.3 Validate policy routing, user config, and local command

`AGENTS.md`가 모든 상세 내용을 포함하지 않고 현재 요청에 필요한 `.podo/policies/`만 읽도록 한다. `user_config.md`의 이름과 성격을 적용하고 `.podo/bin/podo`를 실행할 수 있는지 확인한다.

Pass 조건:

- 관련 정책만 사용하고 무관한 정책의 marker는 출력하지 않는다.
- 누락되거나 깨진 필수 정책에서는 성공한 척하지 않는다.
- 새 작업에서도 합성 비서 이름과 성격을 일관되게 사용한다.
- 명시적 요청 없이 `user_config.md`를 변경하지 않는다.
- Workspace 내부의 hidden entrypoint를 실행할 수 있다.

### 0.4 Define “full Codex original”

Podo가 Event에 보존해야 하는 원본 범위를 먼저 고정한다.

| Data | Requirement |
|---|---|
| User messages | Required |
| Final assistant messages | Required |
| Commentary/progress messages | Required when the surface records them |
| Tool calls and results | Required when the surface exposes them |
| Attachments and stable references | Required when present and exposed |
| Thread/task, turn, and item identifiers | Required when exposed |
| Timestamps | Required when exposed; otherwise capture time is recorded |
| Compaction records | Required when exposed |
| Hidden reasoning | Excluded because it is not a user-visible or supported export surface |
| Credentials and secrets | Never copied intentionally; capture must preserve source security boundaries |

`complete`는 해당 source가 공식적으로 노출하는 모든 required item을 손실 없이 저장했다는 뜻이다. Source가 일부 항목을 제공하지 않으면 `partial`로 기록하고 빠진 범위를 metadata에 명시한다.

### 0.5 Compare transcript acquisition paths

다음 후보를 자동화, 완전성, 현재 작업 식별, 안정성, Desktop 적용성, 보안과 구현 복잡도로 비교한다.

A. 지원되는 thread/task read API

B. Codex App Server의 thread·turn·item API와 stream

C. Codex hook의 `session_id`와 `transcript_path`

D. `$CODEX_HOME/sessions`의 local transcript

Pass 조건:

- 자동 capture에 사용할 primary source 하나와 fallback 하나를 정한다.
- 지원되지 않는 내부 형식에 의존한다면 이를 숨기지 않고 adapter, 감지와 실패 정책을 정한다.
- 자동 capture가 불가능하면 NO-GO로 판단하고 Architecture를 다시 논의한다.

### 0.6 Capture one Event

합성 Codex 작업 하나를 아래 구조로 저장한다.

```text
events/YYYY/MM/<event>/
├── metadata.md
└── original/
    └── <captured-original>
```

Metadata에는 title, occurred/captured time, source type, source entrypoint 또는 identifier, capture method, completeness와 원본 경로를 기록한다.

Pass 조건:

- 실제 합성 Codex 작업의 원본이 자동 저장된다.
- 같은 source를 다시 capture해도 중복 Event가 생기지 않는다.
- source와 completeness를 사람이 이해할 수 있다.

### 0.7 Validate cross-task continuity

첫 작업에서 합성 Event → Delta → State를 만든다. 별개의 새 작업에서 “이전 논의를 이어가자”라고만 요청하고 State-first 복원을 확인한다.

Pass 조건:

- 새 작업이 `user_config.md`와 관련 State를 먼저 읽는다.
- State만으로 부족할 때만 Delta와 Event를 읽는다.
- 현재 결정과 날짜가 있는 TODO를 정확히 설명한다.
- 변화가 없는 대화에서는 파일을 수정하지 않는다.

### 0.8 Exercise critical failures

다음을 확인한다.

- 새 작업과 기존 작업 resume
- transcript compaction 또는 compaction record
- capture 중단과 source 누락
- 현재 작업에서 수정된 `AGENTS.md`의 stale instruction
- 필수 policy 누락 또는 손상
- Event 저장 후 Delta·State 실패
- 같은 source의 중복 capture
- 잘못된 task/thread 선택

Pass 조건:

- 실패를 성공으로 보고하지 않는다.
- 기존 State를 조용히 훼손하지 않는다.
- 재시도에 필요한 source와 중간 결과를 식별할 수 있다.

## Gate

### GO

- policy 적용이 안정적이다.
- full original의 자동 capture가 지원되는 interface로 가능하다.
- 새 작업에서 State 기반 연속성이 재현된다.
- 주요 실패가 기존 State를 훼손하지 않는다.

### CONDITIONAL GO

핵심 흐름은 동작하지만 Desktop transcript capture가 versioned adapter 또는 불안정한 local format에 의존한다. 이 경우 지원 surface, version check, fallback과 명시적 실패를 Phase 1 계약에 포함한다.

### NO-GO

대화 원본 자동 capture 또는 새 작업 연속성이 재현되지 않는다. Architecture를 수정하기 전에는 Phase 1로 넘어가지 않는다.

## Outputs

```text
phase_0/
├── plan.md
├── experiments/
│   ├── 01-workspace.md
│   ├── 02-agents-loading.md
│   ├── 03-policy-config-command.md
│   ├── 04-original-contract.md
│   ├── 05-transcript-sources.md
│   ├── 06-event-capture.md
│   ├── 07-continuity.md
│   └── 08-edge-cases.md
├── findings.md
└── decision.md
```
