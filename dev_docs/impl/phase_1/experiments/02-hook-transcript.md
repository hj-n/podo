# Experiment 02 — Hook and Transcript Contract

## Question

Hook trigger와 versioned transcript adapter의 입력·출력·실패 경계를 구현과 독립적으로 고정할 수 있는가?

## Setup

공식 Codex hook 구조에 맞춰 `Stop` command hook을 정의했다. 별도 JSON contract에 hook 필수 입력과 금지 행동을 기록하고, transcript adapter contract에는 입력, 출력, completeness, fail-closed와 App Server fallback을 정의했다.

Phase 0에서 관찰한 `0.144.0-alpha.4`는 observed version으로만 기록하고 production supported 목록은 비워 두었다.

## Expected

Hook은 source identity만 전달하고 unknown version과 identity mismatch는 fail-closed다.

## Result

Pass for the Phase 1 contract.

- Hook JSON은 유효하며 `Stop`에서 local `.podo/scripts/capture_event`만 호출한다.
- timeout은 30초이고 background 또는 external command가 없다.
- Required identity는 session ID와 turn ID를 모두 포함한다.
- Unknown runtime, source 누락, identity mismatch와 unknown required record family는 fail-closed다.
- App Server historical read는 최대 `partial`로 제한된다.
- Hook target에는 입력을 검증한 뒤 exit 78 `PODO_CAPTURE_NOT_IMPLEMENTED`로 종료하는 fail-closed guard가 있다. 실제 transcript adapter와 Event writer는 아직 없다.

## Evidence

- All hook and contract JSON files passed `jq empty`.
- Hook command: `./.podo/scripts/capture_event`
- Completeness values: `complete-local-transcript`, `partial`
- `production_supported_runtime_versions` is intentionally empty.

## Decision

Hook은 source identity trigger로만 유지한다. Phase 3에서 version-specific adapter와 capture entrypoint가 acceptance를 통과하기 전에는 이 product tree를 설치 가능한 Podo로 공개하지 않는다. 성공하는 placeholder는 만들지 않는다.

Phase 1 guard의 명시적 실패는 placeholder 성공이 아니며 Event, Delta 또는 State를 수정하지 않는다.
