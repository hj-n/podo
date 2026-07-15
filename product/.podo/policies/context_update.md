# Context Update Policy

## Process Previous Captures

Task 시작 시 `./.podo/bin/podo inbox --json`을 실행한다. 결과의 `pending`은 아직 판단하지 않은 이전 turn이고, `deferred`는 이미 한 번 확인이 필요하다고 판단한 내용이다.

- Pending은 `review_entrypoint`의 현재 turn view만 먼저 읽는다.
- 정확한 원문 전체가 필요할 때만 `original_entrypoint`를 읽는다.
- Pending이 기존 deferred 질문에 대한 사용자의 명확한 답이면 resolution으로 처리한다.
- Deferred는 새 task마다 다시 묻지 않는다. 사용자가 해당 주제로 돌아왔거나 pending에 답이 있을 때만 사용한다.

각 pending을 자연스럽게 다음처럼 판단한다.

```text
확인된 실제 변화이며 영향받는 State가 분명함
→ Event → Delta → State

단순 질문·답변, 감사, 반복 정보, 채택되지 않은 아이디어
→ No Delta

추론, 모호한 의도, 중요한 충돌, 큰 영향 또는 민감한 영구 보존
→ 기존 State 유지, 한 번만 defer
```

## Facts, Inferences, Proposals, and Decisions

- 사용자가 명확히 말한 현재 사실, 사용자가 확정한 결정과 검증된 실행 결과는 근거가 될 수 있다.
- Podo가 문맥에서 짐작한 선호·목표·원인은 inference다. 사용자의 사실로 apply하지 않는다.
- “이렇게 해볼 수도 있다”는 proposal이다. 사용자가 채택하지 않았다면 현재 결정이 아니다.
- 사용자가 미확정 충돌을 다음 task에도 기억해 다시 확인해 달라고 명시하면 단순 proposal로 버리지 않고 한 번 defer한다.
- 사용자가 “그렇게 하자”, “바꿔줘”, “TODO로 넣어줘”, “완료했어”처럼 명확히 확정하면 그 요청 자체가 내부 Context 변경의 승인이다.

고정된 입력 category를 만들지 않는다. 실제 문장, 현재 State, 영향 범위, 되돌릴 수 있는지, 민감성과 외부 영향을 함께 본다.

## Apply a Clear Change

사용자가 명확히 확정했고 영향받는 State가 분명하며 외부 행동이 아닌 변화는 다시 묻지 않는다. `.podo-work/requests/<capture-id>.json`을 만들고 실행한다.

```bash
./.podo/bin/podo context apply \
  --capture <capture-id> \
  --request .podo-work/requests/<capture-id>.json
```

Request 형식:

```json
{
  "event": {
    "title": "사람이 이해할 수 있는 Event 제목",
    "context": "이 대화가 들어온 맥락과 왜 미래 판단에 중요한지"
  },
  "updates": [
    {
      "state_slug": "durable-topic-slug",
      "expected_state_sha256": null,
      "delta_title": "실제로 달라진 내용의 제목",
      "changed": "- 이전 Context에서 실제로 달라진 내용",
      "why": "사용자가 명확하게 말한 근거",
      "confidence": "confirmed",
      "needs_confirmation": "- 없음",
      "state_markdown": "# 자유 형식 State Markdown ... {{DELTA_LINK}} ..."
    }
  ]
}
```

`context apply`는 `confirmed`만 허용한다. inference나 확인이 필요한 내용을 State에 넣으려 하지 말고 defer한다.

### State Markdown

State는 고정 category 몇 개로 제한하지 않는다. 주제에 맞는 사람이 읽기 쉬운 Markdown을 유지하고 실제로 영향을 받은 부분만 바꾼다.

- `Updated: YYYY-MM-DD`가 있다.
- 이 변경의 근거 위치에 `{{DELTA_LINK}}`가 정확히 한 번 있다.
- TODO lifecycle은 `.podo/policies/todo.md`를 따른다.
- Existing State는 먼저 읽고 현재 SHA-256을 `expected_state_sha256`에 넣는다.
- New State는 `expected_state_sha256`을 `null`로 둔다.
- 하나의 Event가 여러 State를 바꾸면 `updates`에 각각 넣는다.

기존 결정과 충돌하더라도 사용자가 변경을 명확히 확정했다면 바로 apply한다. `changed`와 `why`에 이전 결론, 새 결론과 변경 이유를 남기고 과거 Event와 Delta는 수정하지 않는다.

## No Delta and Credential Exclusion

미래 판단에 영향을 주는 변화가 없으면 permanent Context를 만들지 않는다.

```bash
./.podo/bin/podo context discard --capture <capture-id> --reason no-delta
```

비밀번호, API key 또는 인증 token이 capture에 들어 있으면 Event로 승격하지 않는다. 임시 원본을 정리하고, 필요한 안전한 Context는 secret 없이 다시 말해 달라고 요청한다.

```bash
./.podo/bin/podo context discard --capture <capture-id> --reason sensitive-data
```

민감 정보가 있다는 사실만으로 다른 명확한 결정을 추측해 재구성하지 않는다.

## Defer Once

의도가 불명확하거나 Podo의 추론이거나 중요한 기존 결정과 모호하게 충돌하거나 여러 State·민감한 원본·외부 영향이 걸려 있으면 permanent Context를 바꾸지 않는다.

`.podo-work/requests/<capture-id>-defer.json`:

```json
{
  "summary": "사용자가 이해할 수 있는 보류 내용 한 줄",
  "why_confirmation": "기존 결정과의 차이 또는 확인이 필요한 이유 한 줄",
  "question": "사용자에게 필요한 최소 질문 한 줄",
  "state_candidates": ["가능한-state-slug"]
}
```

```bash
./.podo/bin/podo context defer \
  --capture <capture-id> \
  --request .podo-work/requests/<capture-id>-defer.json
```

질문할 때 내부 파일이나 판단 category를 나열하지 않는다. 무엇을 바꾸려는지, 기존 무엇과 충돌하는지, 어떤 계획이나 TODO가 영향을 받는지를 high-level에서 설명한다.

## Resolve a Deferred Decision

새 pending capture가 deferred 질문에 대한 명확한 답이면 다음처럼 연결한다.

확인되어 State를 바꿀 때:

```bash
./.podo/bin/podo context resolve \
  --deferred <deferred-capture-id> \
  --capture <confirmation-capture-id> \
  --decision confirmed \
  --request .podo-work/requests/<confirmation-capture-id>.json
```

기각 결과가 미래 State에 중요하지 않을 때:

```bash
./.podo/bin/podo context resolve \
  --deferred <deferred-capture-id> \
  --capture <rejection-capture-id> \
  --decision rejected
```

기각이 현재 State의 잘못된 추론이나 계획을 바로잡아야 한다면 `--request`를 함께 사용해 정정 Delta와 State를 남긴다.

Confirmed/rejected apply의 Event는 새 답변 원본을 주 entrypoint로 사용하고 원래 deferred 원본도 related original로 보존한다. request 없는 rejection은 receipt만 남기며 permanent Context를 만들지 않는다.

## Capture Failure

source identity, supported runtime, completeness 또는 hash를 검증하지 못하면 Delta와 State를 갱신하지 않는다. Partial capture도 전체 원본인 것처럼 apply하거나 defer하지 않는다.

## Report Naturally

Context를 갱신한 뒤에는 command와 파일 목록을 나열하지 않는다. 무엇이 현재 유효해졌고 어떤 TODO가 생기거나 바뀌었는지, 확인할 내용이 남았는지를 간결하게 알린다.
