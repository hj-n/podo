# Context Update Policy

## Process the Previous Turn First

Task 시작 시 `./.podo/bin/podo inbox --json`을 실행한다. Pending capture가 없다면 현재 요청으로 넘어간다.

Pending capture가 있으면 `review_entrypoint`의 현재 turn view만 읽는다. `original_entrypoint`는 전체 session snapshot이므로 정확한 원문 전체가 필요한 경우에만 읽는다.

각 capture를 다음 중 하나로 처리한다.

```text
명확하고 미래에 영향을 주는 변화
→ Event → Delta → State 적용

단순 질문·답변, 반복 정보, 감사와 중간 아이디어
→ No Delta 처리

의도가 불분명하거나 기존 결정과 충돌
→ 기존 State 유지, capture 보존, 사용자 확인
```

## Clear Change

사용자가 결정, 계획 또는 TODO 변화를 명확히 표현했고 영향받는 State가 분명하면 `.podo-work/requests/<capture-id>.json`을 만들고 다음 명령을 실행한다.

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

### State Markdown

State는 고정 category 몇 개로 제한하지 않는다. 주제에 맞는 사람이 읽기 쉬운 Markdown을 유지하고 실제로 영향을 받은 부분만 바꾼다.

필수 조건:

- `Updated: YYYY-MM-DD`가 있다.
- 이 변경의 근거 위치에 `{{DELTA_LINK}}`가 정확히 한 번 있다.
- TODO는 checkbox와 `Created: YYYY-MM-DD`를 가진다.
- Due는 사용자가 정했을 때만 넣는다.
- 완료 TODO는 `Completed: YYYY-MM-DD`를 가진다.
- Existing State는 먼저 읽고 현재 file SHA-256을 `expected_state_sha256`에 넣는다.
- New State는 `expected_state_sha256`을 `null`로 둔다.

하나의 Event가 서로 다른 여러 State를 바꾸면 `updates`에 여러 항목을 넣는다. 각 State에는 별도 Delta가 생기며 Event 원본은 하나만 만든다.

## No Delta

미래 판단에 영향을 주는 변화가 없으면 Event, Delta와 State를 만들지 않는다.

```bash
./.podo/bin/podo context discard \
  --capture <capture-id> \
  --reason no-delta
```

이 명령은 임시 original을 정리하고 source identity와 `no-delta` outcome만 작은 receipt로 남긴다.

## Uncertain Change

의도가 불명확하거나 중요한 기존 결정과 충돌하거나 여러 State에 큰 영향을 주면 apply나 discard를 하지 않는다. 기존 State를 유지하고 무엇을 바꾸려는지, 무엇과 충돌하는지, 어떤 확인이 필요한지를 high-level에서 설명한다.

## Capture Failure

Event original의 source identity, supported runtime, completeness 또는 hash를 검증하지 못하면 Delta와 State를 갱신하지 않는다. Partial capture도 전체 원본인 것처럼 적용하지 않는다.

## Report Naturally

Context를 갱신한 뒤에는 내부 파일과 command를 나열하지 않는다. 무엇이 현재 유효해졌고 어떤 TODO가 생기거나 바뀌었는지 간결하게 알린다.
