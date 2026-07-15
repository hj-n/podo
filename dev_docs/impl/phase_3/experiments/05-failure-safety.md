# Experiment 05 — Failure Safety

## Question

잘못된 source, request, link, date와 stale State가 기존 Context를 보존하는가?

## Setup

Partial capture, stale existing State hash, invalid Updated date와 missing Delta placeholder를 각각 complete baseline Workspace에 주입했다. Adapter failure도 session, turn, runtime과 JSONL별로 분리했다.

## Expected

각 failure는 stable error code로 중단되고 permanent Context hash가 동일하다.

## Result

Pass. 모든 failure가 permanent Event·Delta·State를 변경하지 않았다. Apply 중 문제가 생기면 새 State를 제거하거나 기존 bytes·mode를 복원하고 created Delta·Event를 제거한다.

## Evidence

- `E_CAPTURE_PARTIAL`
- `E_STATE_STALE`
- `E_REQUEST_INVALID_DATE`
- `E_REQUEST_STATE_LINK`
- Adapter의 네 source failure code

## Decision

Partial source와 stale State는 자동 보정하지 않는다. Phase 3 writer는 자신의 apply만 rollback하며, 일반 transaction 진단·복구와 concurrent merge는 Phase 5 범위로 남긴다.
