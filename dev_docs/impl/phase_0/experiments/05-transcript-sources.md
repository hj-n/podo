# Experiment 05 — Transcript Sources

## Question

현재 Codex 작업의 전체 원본과 안정적인 식별자를 자동으로 얻는 primary source와 fallback은 무엇인가?

## Setup

Thread/task read API, App Server, hook `transcript_path`, local session transcript를 공식 문서와 합성 작업으로 비교한다.

## Expected

지원되는 primary source 하나와 현실적인 fallback 하나를 선택하거나, 불가능하면 NO-GO를 선언한다.

## Result

No single supported historical-read API provided every required record in the tested environment. A reliable solution is possible by combining a stable hook identity with a versioned local transcript adapter.

| Candidate | Automatic | Identity | Observed completeness | Stability | Desktop fit | Decision |
|---|---:|---:|---|---|---|---|
| In-agent task/thread read tool | Environment-dependent | Good when present | Not a documented product dependency for every User Workspace | Environment-dependent | Cannot assume availability | Do not use as product foundation |
| App Server `thread/read` | Yes | Strong | User and assistant messages; persisted command/tool items were absent in this test | Supported versioned protocol | Can read the same local session store, but requires a client | Partial fallback and validation source |
| Project hook | Yes | Strong | Supplies session, turn and exact transcript path | Hook fields are supported; pointed transcript schema is explicitly unstable | Good after project trust | Primary identity trigger |
| Direct `$CODEX_HOME/sessions` scan | Yes | Weak without hook | Raw records were richest | Internal file layout/schema | High wrong-task risk | Never select by “newest file” |
| Hook path + local adapter | Yes | Strong | Byte-for-byte raw snapshot including exposed tool records | Adapter is version-dependent | Good after project trust | Conditional primary capture path |

Official documentation confirms that App Server is the deep integration surface for conversation history and streamed events. It also explicitly states that hook `transcript_path` is convenient but its transcript format is not stable.

## Evidence

- Hook events `UserPromptSubmit` and `Stop` both provided the same `session_id`, `turn_id`, `cwd` and exact `transcript_path` for the synthetic turn.
- `thread/read` used that session id successfully and returned one completed turn for the hook task.
- That App Server response contained one `userMessage` and one `agentMessage`; the corresponding local transcript also contained a custom tool call and output.
- The local transcript's `session_meta.id` matched the hook `session_id`.
- A hook did not run while `--ignore-user-config` removed the config layer containing project trust. It ran after using the isolated trusted-project config and explicit test-only hook-trust bypass.
- Official references: [Hooks](https://learn.chatgpt.com/docs/hooks) and [Codex App Server](https://learn.chatgpt.com/docs/app-server).

## Decision

Primary for the initial Desktop-based Podo: a trusted project `Stop` hook provides source identity, then a runtime-versioned adapter snapshots the exact transcript path. It must verify session identity and known record families before claiming `complete-local-transcript`.

Fallback: App Server `thread/read` preserves the supported user/assistant conversation and IDs as `partial`. If neither verified local capture nor App Server read succeeds, Podo must report capture failure and leave State unchanged.

This is a CONDITIONAL-GO result because project hooks require a trusted `.codex/` product surface not present in the current Architecture, and the richest transcript schema is explicitly version-dependent. Phase 1 must not silently add that boundary; it needs an Architecture decision.
