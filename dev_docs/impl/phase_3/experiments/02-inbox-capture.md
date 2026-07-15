# Experiment 02 — Inbox Capture

## Question

Stop hook이 판단 없이 exact transcript를 atomic, immutable과 idempotent한 pending capture로 만들 수 있는가?

## Setup

Synthetic Stop hook payload와 transcript를 installed `capture_event`에 두 번 전달했다. Capture는 `.podo-work/inbox/<session>--<turn>/`에 full session original, current-turn review view와 capture metadata를 기록했다.

## Expected

첫 호출은 한 capture를 만들고 동일 source 재호출은 byte를 바꾸거나 duplicate를 만들지 않는다.

## Result

Pass. 첫 호출은 `captured`, 두 번째는 `already-captured`였고 metadata와 original bytes는 동일했다. Original hash가 source와 일치했고 permanent Event·Delta·State는 바뀌지 않았다.

## Evidence

- Full original: `original/session.jsonl`
- Review view: `turn.jsonl`
- Identity: session+turn-qualified capture ID
- Health: `.podo-work/capture-health.json`
- Python bytecode 생성을 막아 hook 또는 CLI 실행이 product manifest를 바꾸지 않음

## Decision

Inbox capture는 Event가 아닌 user-owned temporary evidence다. Full session bytes는 Event 승격용으로 보존하고, Interface 판단은 target turn만 포함하는 review view를 사용한다.
