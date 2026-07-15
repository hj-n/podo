# Phase 8 Plan — Integration and End-to-End Validation

## Goal

지금까지 따로 검증한 설치, 개인화, Context continuity, 판단, TODO, recovery, product update와 Workspace migration을 실제 사용자 여정처럼 연결한다. 깨끗한 외부 Workspace에서 같은 결과가 반복되고, 한 단계의 성공이나 실패가 다음 단계의 전제를 조용히 깨뜨리지 않는지 확인한다.

Phase 8은 새로운 사용자 데이터 형식이나 제품 기능을 채택하는 단계가 아니다. 통합 과정에서 발견된 결함만 가장 작은 범위로 수정한다.

## Integration Principles

1. 실제 개인 Workspace와 데이터는 사용하지 않는다.
2. 모든 Workspace, transcript, Release와 Codex home은 marker가 있는 disposable fixture다.
3. 한 시나리오 안에서 이전 단계의 실제 출력과 파일을 다음 단계의 입력으로 사용한다.
4. 응답 문구만으로 성공을 판단하지 않고 State, Event, Delta, receipt, journal, backup, version과 실행 명령을 함께 확인한다.
5. 명시적 승인 경계는 시나리오가 길어져도 합치거나 생략하지 않는다.
6. 실패를 주입한 단계는 이전의 유효한 Context를 보존하고, doctor와 startup에서 원인이 구분되어야 한다.
7. 일반 product update와 Workspace migration은 끝까지 별도 흐름으로 유지한다.
8. 실제 Workspace format 2와 public v0.6.0 Release를 만들지 않는다.
9. 테스트가 만든 외부 파일은 marker와 exact parent를 확인한 뒤 항상 정리한다.

## Scenario A — Everyday User Journey

하나의 깨끗한 Workspace에서 다음 상태 전이를 연결한다.

```text
install
→ explicit personalization
→ first decision and TODO
→ Event → Delta → State
→ no-delta conversation
→ new-task State-first restore
→ uncertain conflict defer
→ explicit resolution
→ TODO complete, cancel and reopen
→ final Context validation
```

다음도 함께 확인한다.

- 사용자 설정은 명시적으로 바꾼 내용만 반영된다.
- No Delta는 permanent Context를 바꾸지 않는다.
- 불확실한 충돌은 기존 결정을 덮어쓰지 않는다.
- TODO의 위치와 lifecycle 날짜가 명확하지 않으면 추측하지 않는다.
- 새 task는 필요한 State를 먼저 읽고 불필요한 Event 원문을 다시 읽지 않는다.

## Scenario B — Failure and Recovery Journey

정상 Context가 존재하는 Workspace에서 다음 문제를 각각 연결해 검증한다.

- 두 작업이 같은 State evidence를 기준으로 수정할 때 stale update가 거부된다.
- Context transaction을 중단하면 doctor와 startup이 normal inbox 처리를 멈춘다.
- Recovery plan은 read-only이고 exact approval 뒤에만 적용된다.
- 복구 뒤 이전 Context와 새로 복구된 변경이 모두 검증 가능하다.
- Event original 누락과 State/Delta의 깨진 link는 서로 다른 finding으로 보고된다.
- 의미를 추측해야 하는 손상은 자동 복구하지 않는다.

손상 진단은 복구 가능한 transaction과 별도 fixture에서 검증한다. 일부러 원본을 삭제한 fixture를 정상 상태로 되돌렸다고 가장하지 않는다.

## Scenario C — Product Lifecycle Journey

사용자 Context가 이미 존재하는 Workspace에서 다음 순서를 검증한다.

```text
compatible product update
→ exact-version product rollback
→ incompatible update rejection
→ migration impact plan
→ injected migration failure and exact restore
→ fresh exact migration plan and apply
→ full rollback plan
→ exact full rollback apply
```

각 단계에서 user configuration, 기존 Event·Delta·State, file mode와 Workspace version을 고정해 제품 동작이 사용자 소유 영역을 예상 밖으로 바꾸지 않는지 확인한다.

## Steps

### 8.1 Scenario Contract and Evidence Ledger

- 세 통합 여정의 시작 조건, 상태 전이, 승인 경계와 검증 evidence를 정의한다.
- 각 assertion이 어느 Architecture 약속을 검증하는지 사람이 읽을 수 있게 기록한다.
- 결과를 한눈에 확인할 수 있는 machine-readable run summary 계약을 정한다.

### 8.2 Everyday Journey Harness

- Release package로 빈 외부 Workspace를 설치한다.
- 개인화, Context 생성, No Delta, 새 task 복원, 충돌 해결과 TODO lifecycle을 한 Workspace에서 실행한다.
- 중간 단계마다 permanent Context snapshot과 traceability를 검증한다.

### 8.3 Failure and Recovery Harness

- 정상 여정의 Context를 유지한 채 stale/concurrent apply와 transaction failure를 주입한다.
- doctor, startup, recovery plan, exact apply와 post-recovery validation을 연결한다.
- missing original과 broken link를 read-only doctor finding으로 구분한다.

### 8.4 Product Lifecycle Harness

- compatible update와 exact-version rollback이 같은 사용자 evidence를 보존하는지 확인한다.
- incompatible update가 migration artifact 없이 멈추는지 확인한다.
- synthetic Workspace 1→2 migration의 failure, retry, 성공과 full rollback을 연결한다.

### 8.5 Repeatability and Cleanup Gate

- 세 synthetic journey를 묶은 canonical Phase 8 suite를 제공한다.
- suite를 각각 새 Workspace에서 연속 두 번 실행해 이전 run의 상태에 의존하지 않는지 확인한다.
- run summary와 cleanup evidence가 성공과 실패 양쪽에서 남는지 검증한다.

### 8.6 Real Codex End-to-End Acceptance

- marker-owned Desktop Workspace와 격리한 `CODEX_HOME`을 사용한다.
- 실제 Codex의 여러 새 task에서 개인화, Context 생성·복원, No Delta, 충돌, TODO와 recovery approval을 연결한다.
- 별도의 delivery 구간에서 update-only, migration review/apply와 full rollback review/apply 경계를 다시 확인한다.
- 응답 marker 외에 command trace와 Workspace evidence로 결과를 판정한다.

### 8.7 Full Regression and Phase 9 Handoff

- Phase 1–8 synthetic suite와 주요 실제 Codex acceptance를 실행한다.
- Python/JSON/shell, Git integrity, candidate reproducibility, public Release 분리와 외부 cleanup을 확인한다.
- 발견된 limitation과 GO/NO-GO를 기록하고 dogfooding 범위를 제안한다.

## Meaningful Delivery Units

1. Phase 8 plan과 evidence contract
2. everyday user journey
3. failure and recovery journey
4. product lifecycle journey
5. repeatable synthetic suite
6. real Codex integrated acceptance
7. final regression과 Phase 9 handoff

각 단위는 관련 검증을 통과한 뒤 별도로 commit하고 push한다.

## Exit Criteria

- 세 synthetic journey가 서로 다른 깨끗한 Workspace에서 연속 두 번 통과한다.
- 설치부터 Context 판단·복구·제품 lifecycle까지의 실제 상태 전이가 하나의 결과 summary로 추적된다.
- 실제 Codex의 새 task 사이에서 개인화, State-first continuity와 승인 경계가 유지된다.
- 실패와 손상이 현재 유효한 사용자 Context를 조용히 덮어쓰지 않는다.
- 테스트가 만든 Desktop Workspace, isolated Codex home, Release와 transcript가 marker 검증 뒤 정리된다.
- Phase 1–8 회귀와 static/Git gate가 통과한다.

## Non-Goals

- 실제 개인 Workspace 접근 또는 실제 사용자 데이터 복사
- 실제 Workspace format 2 채택이나 production migration 추가
- 새로운 server, database, daemon 또는 외부 수집
- 자동 손상 복구, backup retention, encryption 또는 remote backup
- Windows native 지원
- Public tag, GitHub Release 또는 v0.6.0 publish
