# Experiment 04 — Full Original Contract

## Question

“Codex 대화 전체 원본”을 검증 가능한 항목과 completeness로 정의할 수 있는가?

## Setup

`plan.md`의 required, conditional, excluded 항목을 실제 source가 노출하는 record와 비교한다.

## Expected

Source별로 `complete` 또는 `partial`을 기계적으로 판정할 수 있고, 숨겨진 reasoning이나 secret 수집을 요구하지 않는다.

## Result

The contract is testable when “complete” is scoped to a named source and runtime.

### Required semantic content

- User-visible user messages
- User-visible assistant progress/commentary and final messages
- Tool or command calls and results exposed by the source
- Stable session/thread, turn and item identifiers exposed by the source
- Source timestamps and attachment references exposed by the source
- Compaction records exposed by the source

### Excluded from completeness

- Hidden chain-of-thought or decrypted reasoning
- Data the source does not expose
- Credentials collected outside the original conversation

The local JSONL can contain an opaque encrypted reasoning record. A byte-for-byte raw snapshot preserves that record, but Podo does not decrypt, interpret or require it when deciding completeness.

Two labels are needed:

- `complete-local-transcript`: every byte from the identified local source snapshot was preserved and the adapter recognized the required record families for this runtime.
- `partial`: the source or adapter omitted or could not recognize one or more required semantic record families.

This is not a claim that one transcript schema is stable across Codex versions.

## Evidence

The tested `0.144.0-alpha.4` local session contained timestamped `session_meta`, `turn_context`, `world_state`, `event_msg` and `response_item` records. Observable payloads included user messages, assistant messages, custom tool calls, custom tool outputs and task lifecycle events.

App Server `thread/read(includeTurns: true)` returned stable thread, turn and item IDs plus user and assistant messages. For the same CLI session it did not return the persisted custom tool call and output present in local JSONL.

Attachments and actual compaction were not present in this synthetic task, so their semantic decoding remains unverified. Unknown raw records would still be preserved by a byte-for-byte snapshot.

## Decision

Use source-qualified completeness, never the ambiguous label `complete` by itself. Preserve the raw identified source before interpreting it, store its SHA-256, and make an unknown schema fail closed or downgrade to `partial`. Treat reasoning records as opaque and outside the supported semantic contract.
