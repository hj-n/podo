# Phase 5 Plan — Safe Updates, Doctor, and Recovery

## Goal

Context 갱신이 어느 단계에서 중단되거나 여러 Codex task가 같은 State를 수정해도 마지막으로 확인된 State를 조용히 훼손하지 않는다. 문제를 숨기거나 추측해 고치지 않고, 읽기 전용 진단과 hash에 고정된 승인 기반 복구를 제공한다.

## Safety Invariants

1. Event, Delta와 State는 하나의 transaction으로 준비한다.
2. 영구 파일을 쓰기 전에 staged 결과 전체를 검증한다.
3. 적용 순서는 Event → Delta → State → receipt다.
4. State를 쓰기 직전에 expected hash를 다시 확인한다.
5. 중단된 transaction은 자동 완료·삭제하지 않는다.
6. `doctor`는 사용자 파일을 수정하지 않는다.
7. `recover`의 plan 생성은 plan artifact 외의 Context와 transaction evidence를 바꾸지 않으며, apply에는 plan ID와 현재 hash 재검증이 필요하다.
8. 원본이나 State의 의미를 추측해 재구성하지 않는다.
9. 손상 파일과 미완료 자료를 사용자 승인 없이 삭제하지 않는다.
10. 복구 실패 시 추가 변경을 멈추고 기존 State와 남은 evidence를 보존한다.

## Transaction Contract

```text
.podo-work/transactions/<transaction-id>/
├── plan.json
├── journal.json
├── staged/
│   ├── event/
│   ├── deltas/
│   ├── states/
│   └── receipts/
└── originals/
```

- `plan.json`: source capture, 목표 경로, 기존 hash, 새 hash와 적용 순서
- `journal.json`: 단계별 시작·완료 시점과 마지막 확인된 결과
- `staged/`: validation을 통과한 exact 적용 후보
- `originals/`: rollback이나 비교에 필요한 기존 State bytes

Transaction 상태는 최소한 `prepared`, `committing`, `recovery-required`, `committed`를 구분한다. Journal은 의미 판단을 하지 않고 실제 완료된 filesystem 단계만 기록한다.

## Recovery Contract

```text
podo doctor [--json]
podo recover [--json]
podo recover --apply <plan-id>
```

- `doctor`: 문제와 evidence만 보고한다.
- `recover`: 현재 상태를 다시 읽어 복구 계획을 만들고 `.podo-work/recovery-plans/`에 저장한다.
- `recover --apply`: 사용자가 확인한 plan ID만 실행한다. 계획 생성 뒤 파일 hash가 달라졌으면 중단한다.

명령은 실제 구현과 테스트가 통과한 뒤에만 README와 canonical command로 공개한다.

## Steps

### 5.1 Failure Model and Contracts

- Phase 3–4 apply, resolve, defer와 receipt 경계를 transaction 관점에서 목록화한다.
- transaction, doctor finding과 recovery plan JSON contract를 정의한다.
- recovery가 자동으로 해도 되는 기계적 조치와 사용자 판단이 필요한 조치를 구분한다.

### 5.2 Prepared Transaction

- 기존 `context apply`가 Event·Delta·State·receipt를 transaction directory에 모두 stage하도록 바꾼다.
- staged 결과와 link, hash, TODO lifecycle을 영구 적용 전에 검증한다.
- 기존 State bytes와 mode를 transaction에 보존한다.
- 정상 apply의 기존 Event·Delta·State 형식과 idempotency를 유지한다.

### 5.3 Journaled Commit and Failure Injection

- Event, 각 Delta, 각 State와 receipt 적용 직전·직후 journal을 기록한다.
- 각 경계에 synthetic failure injection을 제공하되 product의 일반 사용 경로에서는 활성화되지 않게 한다.
- 실패 후 transaction을 `recovery-required`로 남기고 기존 State가 안전한지 증명한다.
- 정상 완료 후 transaction은 작은 committed receipt만 남기고 staged bytes를 정리한다.

### 5.4 Concurrent State Protection

- State 적용 직전 expected hash를 다시 확인한다.
- 변경됐으면 오래된 State 전체를 덮어쓰지 않는다.
- base/current/proposed가 있는 strict 3-way comparison을 수행한다.
- 기계적으로 비중첩인 변경만 병합 후보로 만들고 전체 validator 통과 후 적용한다.
- 같은 줄 또는 같은 TODO/결정 영역 충돌은 recovery-required 또는 user confirmation으로 중단한다.

### 5.5 Read-only Doctor

`doctor`는 다음을 점검한다.

- unfinished transaction과 journal/실제 filesystem 불일치
- Event original, hash와 related original
- Delta → Event/State, State → Delta 링크
- TODO 날짜와 lifecycle
- capture·deferred·receipt 고아 상태
- product manifest와 직접 수정된 제품 파일
- product/Workspace version 호환성
- hook 설치와 최근 capture health

사람용 요약과 안정적인 JSON finding code를 함께 제공한다. 실행 전후 사용자 소유 파일 hash가 같아야 한다.

### 5.6 Recovery Planner

- doctor finding에서 가능한 기계적 복구만 plan으로 만든다.
- transaction을 안전하게 완료할 수 있으면 남은 단계와 영향 파일을 제안한다.
- 영구 적용이 시작되지 않은 transaction은 보존 또는 폐기 선택을 제안하되 자동 삭제하지 않는다.
- receipt 누락은 journal과 영구 파일 hash가 모두 맞을 때만 복원 후보로 만든다.
- deferred/capture 고아는 보존, 다시 pending으로 이동 또는 정리 영향을 설명한다.
- missing original과 damaged State는 자동 내용을 만들지 않고 manual-confirmation-required로 표시한다.

### 5.7 Approved Recovery Apply

- plan ID, expected finding과 모든 관련 hash를 다시 확인한다.
- 승인된 action만 적용하고 각 action을 journal에 기록한다.
- 실패하면 추가 action을 중단하고 새로운 doctor 결과를 남긴다.
- 같은 plan 재실행은 idempotent하거나 stale plan으로 명확히 실패한다.
- recovery 후 Workspace와 Context link를 전체 검증한다.

### 5.8 Synthetic Failure and Concurrency Suite

다음 지점에 실패를 주입한다.

1. staged validation 전후
2. Event 적용 전후
3. Delta 사이
4. State 적용 직전·직후
5. current receipt와 deferred receipt 사이
6. 최종 validation 전후

두 transaction이 같은 State의 서로 다른 부분과 같은 부분을 수정하는 경우를 각각 검증한다. 모든 실패에서 기존 State hash, 남은 transaction과 doctor finding을 확인한다.

### 5.9 Real Codex Recovery Acceptance

Desktop의 marker-owned disposable Workspace에서 실제 새 Codex task들로 다음을 재현한다.

1. 정상 Context 생성
2. 실패 주입으로 interrupted transaction 생성
3. 다음 task에서 자동 적용 없이 문제 발견
4. `doctor` 읽기 전용 진단
5. Interface Codex의 high-level 복구 계획 설명
6. 승인 전 State 무변경
7. 명시적 승인 후 recover apply
8. 다음 task에서 State-first 복원
9. test Workspace, isolated `CODEX_HOME`과 sentinel cleanup

### 5.10 Gate and Phase 6 Handoff

- Phase 1–5 전체 suite를 실행한다.
- JSON, Python syntax, `git diff --check`, product manifest와 Desktop cleanup을 확인한다.
- evidence, limitation과 GO/NO-GO를 기록한다.
- GitHub distribution에서 doctor 결과를 설치/update preflight에 어떻게 연결할지 Phase 6에 넘긴다.

## Meaningful Delivery Units

1. Phase 5 contract와 failure matrix
2. prepared transaction과 staged validation
3. journaled commit과 failure injection
4. concurrency protection
5. read-only doctor
6. recovery planner
7. approved recovery apply
8. synthetic full suite
9. real Codex recovery acceptance
10. final gate와 Phase 6 handoff

각 단위는 관련 검증을 통과한 뒤 별도로 commit하고 push한다.

## Exit Criteria

- 모든 commit 경계에서 강제 중단해도 마지막 정상 State가 훼손되지 않는다.
- interrupted transaction이 남고 다음 task가 이를 자동 적용·삭제하지 않는다.
- `doctor`가 transaction, link, original, receipt와 ownership 문제를 읽기 전용으로 발견한다.
- `recover`가 변경 파일, 보존할 evidence와 복구 불가능 정보를 설명하는 hash-pinned plan을 만든다.
- 승인 전에는 사용자 데이터가 바뀌지 않고 승인 후에는 계획된 action만 적용된다.
- 동시 비충돌 변경은 안전하게 처리되고 충돌 변경은 기존 State를 유지한다.
- 실제 새 Codex task에서 진단 → 설명 → 승인 → 복구 → State-first continuity가 재현된다.

## Non-Goals

- GitHub Release와 remote product update
- Workspace format migration과 backup restore
- 실제 개인 데이터 복구
- 실제 외부 시스템 재시도
- 손상된 State 의미의 무인 자동 재구성
