# Experiment 01 — Versioned Transcript Adapter

## Question

지원 Codex runtime의 local transcript를 정확한 session·turn identity와 record family로 검증할 수 있는가?

## Setup

`codex-cli 0.144.0-alpha.4`에서 관찰한 `session_meta`, `turn_context`와 `response_item` shape를 synthetic JSONL fixture로 만들었다. Product adapter가 session ID, runtime, turn context, user·assistant message와 paired tool record를 분류하게 했다.

## Expected

Known runtime은 deterministic capture metadata를 만들고 unknown runtime, session mismatch와 missing turn은 State 변경 없이 실패한다.

## Result

Pass. Known fixture는 `complete-local-transcript`가 됐다. Unknown runtime, session mismatch, missing turn과 malformed JSONL은 각각 stable error로 실패했다. Assistant record가 없는 fixture는 누락 family를 명시한 `partial`이 됐다.

## Evidence

- Command: `python3 tests/run_phase3_capture.py`
- Runtime: `0.144.0-alpha.4`
- Failures: `PODO_CAPTURE_SESSION_MISMATCH`, `PODO_CAPTURE_TURN_MISSING`, `PODO_CAPTURE_UNSUPPORTED_RUNTIME`, `PODO_CAPTURE_INVALID_TRANSCRIPT`
- Partial evidence: `missing_record_families=["assistant_message"]`

## Decision

지원 runtime을 exact allowlist로 유지한다. User와 assistant message는 complete에 필요하고 tool call·result는 실제로 한쪽이 관찰됐을 때 pair를 요구한다. Opaque record는 원본에 보존하지만 hidden reasoning을 completeness 조건으로 만들지 않는다.
