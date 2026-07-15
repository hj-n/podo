# Podo Implementation Roadmap

이 문서는 [Initial Philosophy](../initial_philosophy.md)와 [Initial Architecture](../initial_architecture.md)를 실제 제품으로 구현하기 위한 큰 단계와 순서를 정의한다.

로드맵의 목적은 모든 기능을 한 번에 만드는 것이 아니라, Architecture의 가장 위험한 전제를 먼저 검증하고 동작하는 Podo를 단계적으로 확장하는 것이다.

## Overall Sequence

```text
Phase 0  핵심 기술 가능성 검증
   ↓
Phase 1  개발 기반과 데이터 계약
   ↓
Phase 2  로컬 설치와 Workspace 생성
   ↓
Phase 3  Event → Delta → State 핵심 루프
   ↓
Phase 4  Podo의 대화와 판단 정책
   ↓
Phase 5  안전한 갱신, 점검과 복구
   ↓
Phase 6  GitHub 배포와 제품 업데이트
   ↓
Phase 7  Workspace Migration과 Rollback
   ↓
Phase 8  통합 테스트와 전체 흐름 검증
   ↓
Phase 9  Dogfooding과 안정화
```

## Milestones

| Milestone | Phases | Outcome |
|---|---|---|
| Prototype | 0–3 | 실제 Codex에서 Context가 이어지는지 검증한다. |
| Usable Alpha | 4–5 | 개인 비서로 안전하게 사용할 수 있다. |
| Installable Beta | 6–7 | 설치, update, migration과 rollback이 가능하다. |
| Stable v1 | 8–9 | 전체 시나리오와 실제 사용을 통해 안정화한다. |

## Development Bootstrap

Phase 0을 시작하기 전에 Development Workspace의 root `AGENTS.md`와 `dev_docs/impl/status.md`를 만든다. `AGENTS.md`는 전체 설계를 반복하지 않고 Source of Truth, 현재 Phase workflow, Workspace 경계, Architecture invariants와 검증 규칙을 연결하는 작은 Development Router로 유지한다.

## Phase 0. Core Feasibility

### Goal

전체 제품을 만들기 전에 Architecture의 핵심 전제가 실제 Codex 환경에서 가능한지 검증한다.

### Work

- User Workspace의 `AGENTS.md`가 Interface Codex에 안정적으로 적용되는지 확인한다.
- `AGENTS.md`가 필요한 `.podo/policies/`를 선택해 읽도록 만들 수 있는지 확인한다.
- 현재 Codex 대화 전체 원본을 자동으로 얻을 수 있는지 확인한다.
- Codex 작업의 링크나 식별자를 Event 출처로 보존할 수 있는지 확인한다.
- 새 Codex 작업에서 기존 State를 찾아 자연스럽게 이어갈 수 있는지 확인한다.
- Interface Codex가 Workspace의 `.podo/bin/podo` 명령을 실행할 수 있는지 확인한다.

### Main Risk

가장 큰 기술 위험은 현재 Codex 대화의 전체 원본을 자동으로 capture할 수 있는지다. 불가능하다면 다음 Phase로 넘어가기 전에 Codex 작업 읽기 도구, 대화 export 또는 별도 capture 수단을 결정한다.

사용자가 매번 대화를 수동 복사하는 방식은 임시 fallback으로만 사용한다.

### Exit Criteria

Codex 대화 하나를 전체 Event로 저장하고, 새로운 Codex 작업에서 그 결과 State를 읽어 이전 대화를 이어갈 수 있다.

## Phase 1. Development Foundation and Data Contracts

### Goal

Development Workspace의 기본 구조와 Podo 데이터 형식을 만든다.

### Work

- Phase 0 전에 만든 개발용 `AGENTS.md`를 검증 결과와 실제 canonical command에 맞게 보완한다.
- 사용자용 `README.md`의 기본 구조를 만든다.
- `product/AGENTS.podo.md`를 만든다.
- `product/.podo/`의 디렉터리 구조를 만든다.
- 제품 `VERSION`과 사용자 `WORKSPACE_VERSION`의 초기 값을 정한다.
- Event Metadata와 전체 원본 구조를 템플릿으로 정의한다.
- Delta 템플릿을 정의한다.
- State와 날짜가 포함된 TODO 템플릿을 정의한다.
- 비서 이름과 성격을 포함하는 `user_config.md` 템플릿을 정의한다.
- 가상의 사용자 데이터만 사용하는 fixture와 테스트 구조를 만든다.
- 파일 경로, 링크와 필수 항목을 검증하는 기본 규칙을 정의한다.

### Exit Criteria

가상의 Podo User Workspace를 손으로 작성하지 않고 템플릿으로 일관되게 생성할 수 있다.

## Phase 2. Local Installation and Development Loop

### Goal

GitHub 배포 전에 로컬 `realpodo`에서 임시 User Workspace를 반복적으로 설치하고 테스트할 수 있게 한다.

### Work

- 로컬 제품 설치 도구를 만든다.
- `product/AGENTS.podo.md`를 User Workspace의 `AGENTS.md`로 설치한다.
- `.podo/` 제품 영역을 설치한다.
- `WORKSPACE_VERSION`, `.podo-work/`, `.podo-backups/`, `user_config.md`, `events/`, `deltas/`와 `state/`를 처음 한 번만 생성한다.
- 기존 사용자 소유 파일을 덮어쓰지 않도록 보호한다.
- `.podo/bin/podo` 기본 entrypoint를 만든다.
- 현재 제품과 Workspace 버전을 보여주는 명령을 만든다.
- 임시 테스트 Workspace를 만들고 제거하는 개발 흐름을 만든다.

### Exit Criteria

한 명령으로 깨끗한 임시 Podo Workspace를 만들고 별도의 Codex 작업으로 열 수 있다.

## Phase 3. Event, Delta, and State Core Loop

### Goal

Podo의 핵심 가치인 Context의 연속성을 end-to-end로 구현한다.

### Work

- 자유로운 대화에서 미래 Context에 영향을 주는 변화를 판단한다.
- 변화가 없다면 Context 파일을 만들거나 수정하지 않는다.
- 의미 있는 Event의 Metadata와 전체 원본을 저장한다.
- Event로 인해 실제로 달라진 내용을 Delta로 만든다.
- 관련 State를 새로 만들거나 영향받은 부분만 수정한다.
- State에서 Delta와 Event 원본까지 추적 가능한 링크를 만든다.
- State에 날짜가 포함된 TODO를 기록한다.
- 관련 State를 먼저 읽고 필요할 때만 Delta와 Event를 읽는다.
- 새로운 Codex 작업에서 이전 논의를 이어간다.

### Development Order

처음에는 하나의 주제와 하나의 State로 전체 흐름을 검증한다. 이후 여러 State와 하나의 Event가 여러 Delta에 영향을 주는 흐름으로 확장한다.

### Exit Criteria

사용자가 새로운 Codex 작업에서 이전 주제를 언급하면 과거를 다시 설명하지 않아도 현재 State와 다음 행동을 복원해 대화를 이어간다.

## Phase 4. Conversation and Decision Policies

### Goal

Podo가 무엇을 직접 반영하고 무엇을 사용자에게 확인해야 하는지 일관되게 동작하도록 만든다.

### Work

- `user_config.md`의 비서 이름, 성격과 대화 방식을 적용한다.
- 명확하고 범위가 작은 변경은 반영한 뒤 사용자에게 알린다.
- 불확실하거나 영향이 큰 변경은 기존 결론을 유지하고 확인받는다.
- 사실, 추론, 제안과 확인이 필요한 내용을 구분한다.
- 기존 결정과 충돌하는 정보를 처리한다.
- 정정 Event와 Delta를 통해 잘못된 State를 바로잡는다.
- 자연어 TODO 추가 요청을 처리한다.
- 관련 State를 추론하고 불명확할 때만 위치를 질문한다.
- TODO의 생성일, 마감일, 완료일과 결과를 관리한다.
- 민감 정보의 원본 보존 여부를 더 보수적으로 판단한다.
- 외부 자료 접근과 외부 행동의 승인 경계를 적용한다.

### Exit Criteria

같은 정책 아래에서 명확한 결정은 자연스럽게 기록하고, 모호하거나 중요한 판단은 사용자 확인 없이 확정하지 않는다.

## Phase 5. Safe Updates, Doctor, and Recovery

### Goal

파일 갱신 도중 중단되거나 여러 Codex 작업이 동시에 수정해도 현재 State가 조용히 훼손되지 않게 한다.

### Work

- `.podo-work/`에 Context transaction을 준비한다.
- 임시 Event, Delta와 변경될 State를 모두 작성한 뒤 검증한다.
- Event, Delta, State 순서로 적용한다.
- State를 쓰기 직전에 동시 변경 여부를 다시 확인한다.
- 깨진 링크, 누락된 원본과 잘못된 날짜를 검사한다.
- 중단된 transaction을 탐지한다.
- 읽기 전용 `podo doctor` 명령을 만든다.
- 복구 계획을 보여주고 승인 후 실행하는 `podo recover` 명령을 만든다.
- State 손상과 잘못된 연결에 대해 추측하지 않는 복원 흐름을 만든다.

### Exit Criteria

Context 갱신을 강제로 중단해도 기존 State가 훼손되지 않는다. `doctor`가 문제를 발견하고 `recover`가 안전한 복구 계획을 제시한다.

## Phase 6. GitHub Distribution and Product Updates

### Goal

다른 User Workspace에서도 README의 명령만으로 Podo를 설치하고 업데이트할 수 있게 한다.

### Work

- 배포 가능한 제품 package를 만든다.
- Semantic Versioning을 적용한다.
- GitHub Release와 Release Notes를 만든다.
- 배포 파일의 checksum을 제공하고 검증한다.
- 최초 설치용 `install.sh`를 만든다.
- README에 실제 설치와 시작 방법을 작성한다.
- 최신 안정 버전과 특정 버전을 다운로드하는 기능을 만든다.
- `.podo/bin/podo update`를 구현한다.
- 직접 수정된 제품 파일을 감지하고 update를 중단한다.
- 제품 적용 후 설치 결과를 검증한다.
- Migration이 없는 버전 rollback을 지원한다.
- Operating Policy가 변경되면 새 Codex 작업을 시작하도록 안내한다.

### Exit Criteria

빈 디렉터리에서 README의 명령 하나로 Podo를 설치하고, 사용자 소유 파일을 유지한 채 다음 제품 버전으로 update와 rollback을 수행할 수 있다.

## Phase 7. Workspace Migrations and Full Rollback

### Goal

사용자 데이터 형식이 바뀌어도 영향을 설명하고 안전하게 이전하거나 원래 상태로 돌아갈 수 있게 한다.

### Work

- 제품 버전과 `WORKSPACE_VERSION`의 호환성을 검사한다.
- `.podo/migrations/`의 실행 구조를 만든다.
- Migration plan과 영향받는 파일을 사용자에게 보여준다.
- Migration에 대한 별도 승인을 받는다.
- `.podo-backups/`에 영향받는 사용자 데이터를 백업한다.
- 필요한 migration을 순서대로 실행한다.
- 실행 후 사용자 데이터 형식을 검증한다.
- 실패하면 이전 제품과 백업된 사용자 데이터를 함께 복원한다.
- 오래된 백업을 사용자 승인 없이 삭제하지 않는다.

### Validation Approach

실제 제품 형식을 억지로 변경하지 않는다. 테스트 fixture에 Workspace 형식 1과 2를 만들어 migration과 rollback 전체 흐름을 검증한다.

### Exit Criteria

가상의 Workspace v1을 v2로 이전할 수 있고, 각 단계에 실패를 주입해도 이전 제품과 사용자 데이터로 복구된다.

## Phase 8. Integration and End-to-End Validation

### Goal

Architecture에서 약속한 주요 흐름이 실제 Codex와 임시 Workspace에서 반복해서 재현되는지 확인한다.

### Scenarios

- 최초 설치와 개인화
- 새로운 Context와 State 생성
- 변화가 없는 대화
- 새 Codex 작업에서 이전 논의 이어가기
- 명확한 결정 변경
- 불확실한 정보와 기존 결정의 충돌
- TODO 추가, 완료, 취소와 위치 선택
- 여러 Codex 작업의 동시 State 수정
- 중단된 Context transaction
- Event 원본 누락과 깨진 링크
- 제품 update와 rollback
- Migration 성공과 실패

### Test Layers

- 파일과 스크립트 단위 테스트
- 가상 User Workspace를 사용하는 통합 테스트
- 실제 Codex 대화를 사용하는 Agent 또는 수동 시나리오 테스트

각 Phase에서 해당 테스트를 함께 만들고, 이 Phase에서는 전체 흐름을 한 번에 검증한다.

### Exit Criteria

주요 사용 시나리오가 실제 Codex와 깨끗한 임시 Workspace에서 반복해서 통과한다.

## Phase 9. Dogfooding and Stabilization

### Goal

실제 `podo-home`을 일정 기간 사용하며 Podo가 Context 복원 비용을 줄이는지 확인하고, 발견된 문제만 근거로 개선한다.

### Observe

- 관련 State를 제대로 찾지 못하는 경우
- 필요 없는 Event가 지나치게 쌓이는지
- 중요한 Delta를 놓치는지
- Podo가 너무 자주 사용자 확인을 요구하는지
- TODO가 잘못된 State에 들어가는지
- State가 시간이 지나며 비대해지는지
- 실패와 복구 안내를 사용자가 이해할 수 있는지
- 이전 Context로 돌아가는 시간이 실제로 줄어드는지

### Evidence-based Extensions

실제 필요성이 확인될 때만 다음을 고려한다.

- 재생성 가능한 검색 Index
- 더 빠른 Context 검색
- 외부 자료 연동
- Background 기능
- 다른 운영체제 지원
- Vector DB 또는 별도 데이터베이스

### Exit Criteria

실제 사용에서 반복적으로 나타난 문제를 수정하고, Podo가 사용자의 과거 설명 비용을 줄인다는 것을 확인한다.

## Rules Across All Phases

- 실제 개인 데이터를 개발 fixture나 테스트에 사용하지 않는다.
- 각 Phase는 이전 Phase의 완료 기준을 만족한 뒤 진행한다.
- Architecture와 다른 구현이 필요해지면 조용히 변경하지 않고 이유와 영향을 먼저 문서화한다.
- 제품 파일과 사용자 소유 파일의 경계를 모든 Phase에서 유지한다.
- 기능 구현과 함께 해당 단위의 검증을 추가한다.
- 필요한 부분만 수정하고 관련 없는 정책이나 문서를 다시 쓰지 않는다.
