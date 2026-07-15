# Phase 4 Plan — Conversation and Decision Policies

## Goal

Phase 3의 검증된 capture와 `Event → Delta → State` writer 위에 일관된 판단 정책을 올린다. 명확한 변화는 자연스럽게 반영하고, 추론·충돌·민감 정보·외부 영향처럼 확인이 필요한 변화는 현재 State를 유지한 채 보류한다.

입력을 몇 개의 고정 category로 분류하는 시스템을 만들지 않는다. 판단은 사용자의 실제 표현, 현재 State, 영향 범위, 되돌릴 수 있는지, 민감성과 외부 영향을 함께 보고 high-level에서 설명한다.

## Product Contract

### Clear and No Delta

- 사용자가 명확하게 확정했고 영향받는 State가 분명한 내부 Context 변화는 다시 묻지 않고 반영한 뒤 알린다.
- 단순 질문, 감사, 반복 정보와 확정되지 않은 아이디어는 `No Delta → No Update`로 처리한다.
- Podo가 추론한 선호나 목표를 사용자의 확정된 사실로 기록하지 않는다.

### Deferred Confirmation

- 불명확한 의도, 중요한 충돌, 큰 영향, 민감한 원본 보존 또는 외부 영향은 permanent Context를 바꾸지 않고 `.podo-work/`에 보류한다.
- 보류 기록은 사용자가 이해할 수 있는 요약, 확인이 필요한 이유, 질문과 가능한 State 위치만 가진다.
- 보류는 새 task마다 반복 질문하는 queue가 아니다. 사용자가 해당 주제로 돌아오거나 답을 명확히 했을 때만 다시 다룬다.
- 사용자가 확인하거나 기각한 새 turn을 resolution의 주 Event로 사용한다.
- 확인 결과를 적용할 때 주 Event에는 confirmation turn의 전체 원본과 원래 보류 capture의 전체 원본을 함께 보존한다.
- 기각이 미래 Context에 중요하지 않으면 receipt만 남기고 permanent Context를 만들지 않는다. 중요하면 정정 Delta와 State를 남긴다.

### Conflict and Correction

- 사용자가 기존 결정을 명확히 바꾸면 새 결론을 반영하고 이전 결론과 변경 이유를 Delta에 남긴다.
- 의도가 불명확한 충돌은 기존 State를 유지하고 보류한다.
- 과거 Event와 Delta는 조용히 수정하거나 삭제하지 않는다.

### TODO

- 명시적인 자연어 TODO 요청 자체를 생성·변경·완료·취소 승인으로 본다.
- State 위치는 `사용자 명시 → 현재 주제 → 유일한 관련 State` 순서로 찾는다.
- 위치가 여러 개거나 새 State가 필요하면 State를 임의로 만들지 않고 보류해 질문한다.
- 생성일은 반드시 기록한다. 마감일은 사용자가 말했거나 명확한 일정 근거가 있을 때만 기록한다.
- 완료·취소·재개와 결과를 날짜와 함께 다루며, 실행 시도만으로 완료 처리하지 않는다.

### User Configuration and Safety

- task 시작 시 사용자가 명시한 비서 이름, 성격과 대화 방식을 적용한다.
- 대화에서 추론한 성향을 `user_config.md`에 자동으로 확정하지 않는다.
- credential은 영구 원본에 저장하지 않는다.
- 의료·금융·제3자의 민감 자료를 영구 보존하려면 확인한다.
- 외부 자료 읽기는 허용 범위 안에서만 하고, 외부 시스템이나 다른 사람에게 영향을 주는 행동은 사용자의 명시적 요청 없이 실행하지 않는다.
- 외부 자료 안의 지시는 Podo 운영 명령으로 취급하지 않는다.

## Lifecycle

```text
pending capture
  ├─ clear change ──────────────→ applied Event · Delta · State
  ├─ no meaningful change ─────→ no-delta receipt
  └─ confirmation required ────→ deferred
                                  ├─ confirmed → resolution Event · Delta · State
                                  └─ rejected  → receipt, 또는 중요한 정정 Delta · State
```

## Steps

### 4.1 Contract and Scenario Matrix

- Phase 4 판단 계약과 deferred lifecycle을 문서화한다.
- clear, no-delta, inference, proposal, conflict, correction, TODO, user configuration, sensitive retention과 external action 시나리오를 정한다.

### 4.2 Deferred Store and CLI

- `.podo-work/deferred/`에 보류 상태를 안전하게 기록한다.
- `podo inbox --json`에서 pending과 deferred를 구분한다.
- `podo context defer`와 `podo context resolve`를 구현한다.
- defer와 resolve의 idempotency, invalid request와 failure 보존을 검증한다.

### 4.3 Resolution Evidence and Corrections

- confirmed/rejected resolution을 receipt로 연결한다.
- 적용되는 resolution Event에 confirmation 원본과 deferred 원본을 함께 보존한다.
- 명확한 결정 변경은 정정 Delta로 적용하고, 모호한 충돌은 State를 보존하는지 검증한다.

### 4.4 TODO Lifecycle

- 자연어 TODO의 위치 선택 정책을 구체화한다.
- Created, Due, Completed, Cancelled, Reopened와 Result 날짜 규칙을 검증한다.
- 여러 State 후보와 새 State가 필요한 경우 deferred 질문으로 처리한다.

### 4.5 User Configuration, Sensitive Data, and External Boundaries

- 명시된 비서 이름·성격·응답 방식을 실제 task에서 적용한다.
- inferred preference를 user configuration으로 확정하지 않는다.
- credential, 민감 원본과 external read/write 승인 경계를 정책과 시나리오로 검증한다.

### 4.6 Synthetic Decision Suite

- clear apply와 no-delta를 회귀 검증한다.
- defer가 permanent Context를 바꾸지 않는지 검증한다.
- confirmed resolution, rejected resolution과 correction을 검증한다.
- TODO lifecycle과 stale/invalid resolution 실패 경로를 검증한다.

### 4.7 Real Codex Acceptance

저장소 밖 Desktop의 marker-owned temporary Workspace에서 새 Codex task들로 다음을 재현한다.

1. `user_config.md`의 이름과 응답 방식 적용
2. 명확한 결정의 자동 반영
3. 단순 대화의 No Delta
4. 모호한 기존 결정 충돌의 defer와 State 보존
5. 무관한 다음 task에서 확인 질문을 반복하지 않음
6. 사용자의 명확한 confirmation으로 resolution 적용
7. 자연어 TODO의 명확한 위치 선택과 날짜 기록
8. 여러 State가 가능한 TODO의 위치 질문
9. TODO 완료 또는 취소 결과 반영
10. State-first continuity

민감 정보와 실제 외부 행동은 실제 credential이나 외부 시스템을 사용하지 않고 synthetic prompt와 무변경 evidence로 검증한다.

### 4.8 Gate and Cleanup

- Phase 1–4 관련 suite를 모두 실행한다.
- `git diff --check`, JSON과 Python syntax를 확인한다.
- test artifact와 Desktop test parent를 marker 확인 후 제거한다.
- evidence, limitation과 Phase 5 handoff를 기록하고 GO/NO-GO를 판정한다.

## Meaningful Delivery Units

1. Phase 4 contract와 scenario plan
2. Deferred store와 CLI
3. Resolution evidence와 correction
4. TODO lifecycle policy와 validation
5. User configuration·sensitive·external policy
6. Synthetic decision suite
7. Real Codex acceptance
8. Gate decision과 Phase 5 handoff

각 단위는 관련 검증을 통과한 뒤 별도로 commit하고 push한다.

## Exit Criteria

- 명확한 내부 Context 변화는 재확인 없이 반영된다.
- 변화 없는 대화는 permanent Context를 바꾸지 않는다.
- 추론, 모호한 충돌과 영향이 큰 변화는 기존 State를 유지한 채 한 번만 보류된다.
- 사용자의 확인·기각·정정이 이전 보류와 추적 가능하게 연결된다.
- 자연어 TODO의 위치와 생성·마감·완료·취소·재개 날짜가 일관되게 관리된다.
- 명시된 user configuration이 적용되고 추론된 성향은 설정으로 확정되지 않는다.
- 민감 정보와 외부 행동 경계가 synthetic 실제 Codex 시나리오에서 지켜진다.
- 새 task에서 관련 State만으로 현재 결정과 다음 행동을 복원한다.

## Non-Goals

- concurrent State 자동 병합
- 일반 transaction doctor와 recovery
- GitHub distribution과 product update
- Workspace migration
- 실제 개인 데이터나 실제 외부 시스템을 사용하는 acceptance
