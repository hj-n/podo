# Experiment 06 — Event Capture

## Question

합성 Codex 작업을 source, completeness와 전체 원본을 가진 Event로 자동 저장하고 중복을 막을 수 있는가?

## Setup

A disposable `capture_event.py` prototype received a saved synthetic `Stop` hook record and the User Workspace path.

Before writing, it:

1. required a `Stop` event with session and turn IDs,
2. required the source transcript to exist,
3. matched `session_meta.id` to the hook session ID,
4. recognized required record families,
5. derived a deterministic Event path from occurred time and turn ID,
6. copied the source bytes before writing metadata,
7. stored a SHA-256 and source-qualified completeness.

## Expected

Event 하나가 규정된 경로에 저장되고 같은 source의 재실행은 같은 Event를 식별한다.

## Result

Pass for the tested local transcript adapter.

The first run created:

```text
events/2026/07/2026-07-15_034319-codex-019f63df/
├── metadata.md
└── original/
    └── session.jsonl
```

The second identical run returned `ALREADY_CAPTURED` and did not create another Event. The captured file hash matched metadata.

## Evidence

- Source session: `019f63df-334f-7523-add0-489b9bd3f795`
- Source turn: `019f63df-338e-7552-8f0b-61c86d48e826`
- Runtime recorded in metadata: `0.144.0-alpha.4`
- Completeness: `complete-local-transcript`
- Missing required record types: `none`
- Metadata links to `original/session.jsonl` and records source entrypoint, method and SHA-256.
- All raw evidence remains under the disposable `/tmp` Workspace and is not committed.

## Decision

The Event directory and metadata shape are feasible. Idempotency must be keyed by both session and turn, because one session transcript can grow after resume. Once captured, an Event is an immutable turn snapshot; a later turn becomes a separate Event. Production code must move the temporary write and atomic apply behavior into the later transaction phase.
