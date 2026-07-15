# Phase 3 — Event, Delta, and State Core Loop

## Goal

자연스러운 Codex 대화에서 미래 Context에 영향을 주는 변화만 골라 전체 원본이 있는 Event, 실제 변화인 Delta와 현재 유효한 State로 연결한다. 새로운 Codex 작업은 State부터 읽어 이전 설명 없이 대화를 이어간다.

```text
Stop hook의 정확한 transcript
        ↓
.podo-work/inbox의 임시 capture
        ↓ Interface Codex가 의미 판단
의미 있음                  변화 없음
   ↓                          ↓
Event → Delta → State       No Delta receipt
```

Hook은 source identity와 원본 capture만 담당한다. Event 승격, Delta 판단과 State 갱신은 Interface Codex가 policy와 installed CLI를 통해 수행한다.

## Why an Inbox Exists

Stop hook이 실행될 때는 해당 turn의 assistant 판단이 이미 끝났고, hook 자체는 판단이나 State 갱신을 하면 안 된다. 반대로 turn 도중에는 정확한 transcript path와 turn ID를 안정적으로 알 수 없다.

따라서 hook은 모든 turn을 Event로 만들지 않고 `.podo-work/inbox/`에 검증된 임시 capture만 둔다. 다음 Interface 작업은 사용자 요청을 처리하기 전에 이전 capture를 분류한다.

- 의미 있는 변화: immutable Event로 승격하고 Delta·State 적용
- 변화 없음: Event를 만들지 않고 작은 processed receipt만 남김
- 불확실하거나 충돌: 기존 State를 유지하고 capture를 보존한 채 확인

이 inbox는 Podo의 영구 Context Store가 아니라 다음 Interface 작업이 처리할 user-owned 작업 영역이다.

## Scope

Phase 3에서 한다:

- `codex-cli 0.144.0-alpha.4`용 versioned local transcript adapter
- session·turn identity, runtime, record family와 원본 hash 검증
- atomic, immutable, idempotent inbox capture
- meaningful capture의 Event 승격
- 하나의 Event에서 하나 또는 여러 Delta·State 갱신
- 자유 형식 State Markdown과 날짜가 있는 TODO 검증
- `No Delta → No Update` 처리와 receipt
- installed CLI의 `inbox`, `context apply`, `context discard`
- hook health와 capture readiness 표시
- synthetic transcript 계약·실패 테스트
- Desktop의 실제 Codex 작업에서 capture → apply → 새 작업 restore

Phase 3에서 하지 않는다:

- 불확실한 변경을 자동 확정하는 고급 판단 정책
- 동시에 실행되는 여러 Codex 작업의 자동 병합
- 중단된 transaction의 일반 `doctor`와 `recover`
- GitHub 배포, product update와 migration
- transcript format을 여러 Codex runtime에 추측으로 적용
- 외부 서비스, database, daemon 또는 background monitor

## Ownership and Safety

- Inbox, request, receipt와 rollback 자료는 user-owned `.podo-work/`에 둔다.
- Event, Delta와 State만 영구 Context다.
- 원본은 Workspace 밖으로 전송하지 않는다.
- 지원하지 않는 runtime, identity mismatch, 누락 source 또는 unknown record shape는 State를 바꾸지 않고 실패한다.
- API key, auth file과 hidden reasoning을 별도로 추출하거나 복호화하지 않는다.
- Event original은 승격 뒤 수정하지 않는다.
- Context apply는 Event → Delta → State 순서로 적용하고 실패 시 이번 실행의 변경만 되돌린다.
- Existing State를 갱신할 때 expected hash가 다르면 중단한다. 일반적인 concurrency 해결은 Phase 5 범위다.

## Installed Flow

### Stop hook

`capture_event`는 hook JSON을 stdin으로 받아 다음을 수행한다.

1. Workspace와 exact source identity 확인
2. transcript의 session ID와 Codex runtime 확인
3. current turn ID 존재 확인
4. supported record family 분류
5. source bytes를 temporary directory에 복사
6. hash와 capture metadata 기록
7. `.podo-work/inbox/<session>--<turn>/`로 atomic apply
8. hook health 기록과 supported JSON status 반환

같은 session+turn을 다시 받으면 기존 capture hash를 확인하고 `already-captured`로 끝낸다.

### Start of the next Interface task

Interface `AGENTS.md`는 user config를 읽은 뒤 `podo inbox --json`을 먼저 확인한다. Pending capture가 있으면 Context update policy를 읽는다.

- 명확한 변화: request JSON을 `.podo-work/requests/`에 만들고 `podo context apply` 실행
- 변화 없음: `podo context discard --reason no-delta` 실행
- 불확실: capture를 남기고 사용자에게 high-level 확인

이 처리가 끝난 뒤 현재 요청에 관련된 State를 복원한다.

### Context request

Request는 미리 정한 몇 개의 기억 category로 State를 제한하지 않는다. 각 update가 완성된 자유 형식 `state_markdown`과 Delta 설명을 제공한다.

```json
{
  "event": {
    "title": "Synthetic planning decision",
    "context": "사용자가 합성 계획을 명확히 결정했다."
  },
  "updates": [
    {
      "state_slug": "synthetic-planning",
      "expected_state_sha256": null,
      "delta_title": "Meeting time decided",
      "changed": "- 회의 시간을 금요일 오전 9시로 결정했다.",
      "why": "사용자가 직접 결정했다.",
      "confidence": "confirmed",
      "state_markdown": "# ... {{DELTA_LINK}} ..."
    }
  ]
}
```

Existing State는 current hash를 request에 포함한다. 하나의 Event가 여러 주제를 바꾸면 `updates`에 여러 State를 넣고 각 Delta가 같은 Event를 참조한다.

## Meaningful Units

1. Phase 3 execution contract
2. Transcript adapter and inbox capture
3. Event·Delta·State apply and No Delta handling
4. Contract and failure suite
5. Real Codex cross-task acceptance
6. Gate and Phase 4 handoff

각 단위는 관련 검증을 통과한 뒤 commit하고 push한다.

## Steps

### 3.1 실행 계약과 실험 구조

Inbox가 필요한 이유, 영구 Event와 임시 capture의 차이, 지원 runtime, 실패 경계와 gate를 문서화한다.

### 3.2 Transcript fixture와 adapter

현재 runtime의 synthetic JSONL fixture를 만들고 session metadata, turn identity, user·assistant message와 tool pair를 분류한다. Unknown runtime이나 source mismatch는 stable error로 실패한다.

### 3.3 Inbox capture

Guard를 실제 capture entrypoint로 교체한다. Atomic write, source-qualified ID, hash, idempotency와 health receipt를 구현한다.

### 3.4 Installed CLI inbox

`podo inbox --json`이 Development Workspace 없이 pending capture의 ID, time, completeness와 안전한 preview를 보여준다.

### 3.5 Context apply request

Event metadata, 하나 이상의 Delta와 자유 형식 State candidate를 staging에서 조립한다. 모든 path, link, TODO date와 expected State hash를 쓰기 전에 검사한다.

### 3.6 Event 승격

Inbox original을 immutable Event로 복사하고 metadata에 session, turn, runtime, completeness와 source hash를 기록한다. 같은 capture의 반복 적용은 duplicate Event를 만들지 않는다.

### 3.7 Delta와 State 적용

Event → Delta → State 순서로 적용한다. State에는 해당 Delta link가 있어야 하며 실제로 영향받은 State만 쓴다. 실패 시 created Event·Delta를 제거하고 기존 State를 복원한다.

### 3.8 No Delta

`context discard`는 Event·Delta·State를 만들지 않고 inbox original을 제거한 뒤 source ID와 `no-delta` outcome만 receipt로 남긴다.

### 3.9 Multiple State

하나의 capture가 서로 다른 두 State에 영향을 주는 request를 적용해 하나의 Event와 두 Delta, 두 State link를 확인한다.

### 3.10 Failure suite

Unknown runtime, session mismatch, missing turn, malformed JSONL, partial record family, Event collision, broken State link, invalid TODO date와 stale State hash를 검증한다.

### 3.11 Interface policy

작은 `AGENTS.md` router와 context update policy가 inbox 확인, clear apply, no-delta discard와 uncertain preserve를 이해하기 쉽게 안내하도록 갱신한다.

### 3.12 Real Codex capture acceptance

Desktop marker-owned Workspace에서 새 Codex task를 실행하고 Stop hook이 실제 inbox capture를 만드는지 확인한다.

### 3.13 Cross-task continuity acceptance

두 번째 Codex task가 이전 capture를 Event·Delta·State로 적용하고 현재 결정과 날짜가 있는 TODO를 복원하는지 확인한다. 세 번째 no-delta task는 permanent Context hash를 바꾸지 않아야 한다.

### 3.14 Gate와 cleanup

전체 Phase 1–3 suite를 실행하고 marker-owned Workspace와 isolated Codex home을 제거한다. README, findings, decision과 status를 실제 결과에 맞춘다.

## Exit Criteria

- 지원 runtime의 실제 Stop hook이 exact session+turn transcript를 inbox에 idempotent하게 capture한다.
- 의미 있는 synthetic capture가 immutable Event, traceable Delta와 현재 State가 된다.
- 하나의 Event에서 여러 State를 안전하게 갱신할 수 있다.
- No Delta task는 Event·Delta·State를 바꾸지 않는다.
- 새 Codex 작업이 State부터 읽어 이전 결정과 날짜가 있는 TODO를 사용자 재설명 없이 복원한다.
- Unsupported or damaged source는 기존 State를 유지한다.
- Desktop test artifact가 marker 확인 뒤 모두 정리된다.

