# Phase 1 — Development Foundation and Data Contracts

## Goal

Podo의 제품 원본 구조와 사람이 읽을 수 있는 Context 데이터 계약을 만든다. Phase 2의 설치 도구와 Phase 3의 실제 Context 갱신 루프가 같은 파일 형식을 사용하도록, 먼저 경계와 검증 규칙을 고정한다.

## Scope

Phase 1에서 한다:

- 배포 원본인 `product/` 구조 생성
- Interface `AGENTS.podo.md`, project hook과 상세 정책의 기본 계약 정의
- Codex transcript adapter 입력·출력과 실패 규칙 정의
- 제품·Workspace 버전과 소유권 계약 정의
- Event, Delta, State, TODO와 `user_config.md` 템플릿 생성
- synthetic fixture 조립과 정적 validator 구현
- README의 제품 소개, 데이터 경계와 hook 안내 기본 구조 작성

Phase 1에서 하지 않는다:

- 실제 User Workspace 설치·업데이트·rollback
- 실제 transcript를 Event로 자동 capture하는 production adapter
- 대화 의미를 판단해 Delta와 State를 자동 갱신하는 전체 루프
- transaction, migration, doctor와 recover 구현
- GitHub Release 또는 작동한다고 공개하는 install command

## Meaningful Units

1. Phase 1 실행 계약
2. 제품 구조와 Codex 연결 계약
3. Context 데이터 계약과 템플릿
4. fixture 조립과 validator
5. 통합 gate와 handoff

각 단위는 관련 검증을 통과한 뒤 commit하고 push한다.

## Steps

### 1.1 Phase 1 실행 계약

이 plan, 실험 문서, findings와 decision 구조를 만든다. Phase 0에서 남은 조건을 Phase 1의 명시적 acceptance로 옮긴다.

Pass 조건: 모든 Phase 1 산출물과 제외 범위를 어느 Step에서 다루는지 알 수 있다.

### 1.2 제품 구조와 소유권

`product/AGENTS.podo.md`, `product/.codex/hooks.json`, `product/.podo/`의 추적 가능한 기본 구조를 만든다. 제품 소유 경로와 사용자 소유 경로를 기계적으로 비교할 수 있게 정의한다.

Pass 조건: update 가능 영역과 보존해야 할 사용자 영역이 겹치지 않는다.

### 1.3 버전 계약

제품 `VERSION`, 사용자 데이터 `WORKSPACE_VERSION`의 초기값과 형식을 정한다. Phase 1에서는 migration을 구현하지 않고 호환성 판단에 필요한 계약만 만든다.

Pass 조건: 제품 버전과 Workspace 형식 버전을 혼동하지 않고 validator가 각각 검사한다.

### 1.4 Interface policy router

`AGENTS.podo.md`를 작은 진입점으로 작성한다. 역할, 제품·사용자 경계, `user_config.md`, State-first, 정책 routing, `No Delta → No Update`와 missing-policy 실패를 포함한다.

Pass 조건: 상세 정책 내용을 root 파일에 복제하지 않고 필요한 정책 경로를 찾을 수 있다.

### 1.5 Hook 계약

`Stop` hook이 `.podo/scripts/capture_event`를 호출하도록 정의한다. Hook은 Codex가 제공하는 JSON을 stdin으로 전달할 뿐, Event·Delta·State를 직접 변경하지 않는다.

Pass 조건: hook 형식이 유효하고 외부 전송, background process 또는 trust 우회를 포함하지 않는다.

### 1.6 Transcript adapter 계약

정확한 runtime version, session ID, turn ID와 transcript path를 입력으로 받는 adapter 계약을 정의한다. raw snapshot, hash, completeness와 missing record families를 출력한다.

Pass 조건: unknown version, source 누락과 identity 불일치가 fail-closed이며 App Server fallback은 `partial`로 구분된다.

### 1.7 Event 계약과 템플릿

session+turn 기준의 immutable Event snapshot, Metadata 필수 항목, original entrypoint, SHA-256, completeness와 민감 정보 경계를 정의한다.

Pass 조건: validator가 정상 Event와 누락·깨진 Event를 구분한다.

### 1.8 Delta 계약과 템플릿

근거 Event, 실제 변화, 영향받는 State, 이유, 추론과 확인 필요 사항을 기록하는 형식을 만든다.

Pass 조건: Delta가 존재하는 Event와 State를 모두 추적할 수 있다.

### 1.9 State와 TODO 계약

State의 자유로운 문서 구조를 유지하면서 현재 Context, 결정, TODO와 중요한 근거를 찾을 수 있게 한다. TODO 날짜와 완료 결과 규칙을 정의한다.

Pass 조건: 고정된 주제 category를 강요하지 않으면서 필수 TODO 날짜를 검사할 수 있다.

### 1.10 User Configuration 계약

비서 이름, 성격, 대화 방식, 사용자 기본값과 허용한 외부 자료 범위를 자유롭게 적을 수 있는 템플릿을 만든다.

Pass 조건: 명시된 값과 예시를 구분하고 추론한 성향을 자동 설정으로 만들지 않는다.

### 1.11 Fixture와 validator

정상 synthetic Workspace와 주요 손상 fixture를 만들고 표준 platform 도구만 사용하는 validator를 구현한다.

검사 대상:

- 필수 경로와 파일
- 제품·사용자 소유권
- 버전과 날짜 형식
- Event → Delta → State 링크
- Event original과 hash
- source identity와 completeness
- TODO의 Created 및 선택적 날짜

Pass 조건: 정상 fixture는 통과하고 각 손상 fixture는 예상한 code와 이유로 실패한다.

### 1.12 Template 조립과 gate

개발용 helper로 템플릿을 두 개의 disposable Workspace에 각각 조립한다. 결과가 결정적이고 validator를 통과하는지 확인한다. README, findings와 decision을 마무리한다.

Pass 조건:

- 같은 입력으로 조립한 Workspace의 계약 대상 파일이 동일하다.
- 실제 개인 데이터나 실제 transcript가 포함되지 않는다.
- 정상·주요 실패 검증이 모두 재현된다.
- Phase 2가 설치 흐름을 구현할 수 있을 만큼 제품 원본과 계약이 완성된다.

## Phase 0 Conditions Carried Forward

- `.codex/hooks.json`은 승인된 product-owned file이다.
- transcript adapter는 exact runtime version으로 선택한다.
- unknown schema와 source identity 불일치는 성공으로 처리하지 않는다.
- App Server historical read는 검증된 범위에서 `partial` fallback이다.
- Desktop hook trust, attachment와 post-compaction capture는 production adapter acceptance에 남긴다.
- README는 hook 검토와 raw Event의 민감성을 설명한다.

## Outputs

```text
dev_docs/impl/phase_1/
├── plan.md
├── experiments/
│   ├── 01-structure-policy.md
│   ├── 02-hook-transcript.md
│   ├── 03-context-contracts.md
│   ├── 04-validator-fixtures.md
│   └── 05-integration.md
├── findings.md
└── decision.md
```

## Exit Criteria

가상의 Podo User Workspace를 손으로 작성하지 않고 템플릿으로 일관되게 생성하고, 정상 구조와 주요 손상을 validator로 구분할 수 있다.
