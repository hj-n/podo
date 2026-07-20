# People Policy

## Separate Current Store

People은 State category가 아니다. `people/<person-slug>.md`에서 사람을 중심으로 이름과 별칭, 사용자와의 관계, 현재 맥락, 함께 진행하는 일과 중요한 근거를 관리한다.

TODO의 정본은 계속 관련 `state/`에 둔다. People에는 TODO checkbox를 복사하지 않고 관련 State 또는 TODO가 있는 문서의 Markdown link를 둔다.

## Identity

이름, 별칭 또는 현재 대화로 기존 한 사람을 명확하게 식별할 수 있을 때만 해당 People 파일을 갱신한다. 동명이인, 같은 별칭 또는 관계 설명 충돌로 둘 이상이 가능하면 후보를 보여주고 최소한의 구분을 질문한다.

사용자가 사람을 명확히 소개하고 지속적으로 기억해 달라는 맥락이면 새 People 파일을 만들 수 있다. Podo가 잠깐 언급된 이름만 보고 장기적인 사람 기록을 자동 생성하지 않는다.

## Safe Content

- 사용자가 말한 현재 관계와 확인된 사실을 Podo의 해석과 구분한다.
- 성격, 의도, 건강, 재정과 같은 민감하거나 추론적인 내용을 사실처럼 확정하지 않는다.
- 비밀번호, 인증 token과 다른 secret은 기록하지 않는다.
- 기존 관계 설명과 새 설명이 모호하게 충돌하면 기존 내용을 유지하고 확인한다.

## Context Update

명확한 People 변화는 일반 Context transaction에서 `target_kind: people`로 Event와 Delta를 먼저 만들고 People 파일을 마지막에 갱신한다. 새 파일은 `expected_person_sha256: null`, 기존 파일은 현재 hash를 사용한다.

People Markdown의 변경 근거에는 `[Delta]({{DELTA_LINK}})`를 정확히 한 번 둔다. `{{DELTA_LINK}}`는 plain text나 별도 field가 아니라 Markdown link의 목적지여야 한다.

```json
{
  "target_kind": "people",
  "person_slug": "kim-minsu",
  "expected_person_sha256": null,
  "delta_title": "민수와의 관계 맥락 추가",
  "changed": "- 민수는 사용자의 대학 친구다.",
  "why": "사용자가 명확히 소개했다.",
  "confidence": "confirmed",
  "needs_confirmation": "- 없음",
  "person_markdown": "# 김민수\n\nName: 김민수\nAliases: 민수\nUpdated: 2026-07-20\n\n## Current Context\n\n대학 친구다.\n\n## Reasons\n\n- [Delta]({{DELTA_LINK}})\n"
}
```
