# Experiment 04 — Failure Injection and Rollback

## Question

설치 단계별 실패가 기존 target을 보존하고 이번 실행이 만든 경로만 정리하는가?

## Setup

`after-staging`, `after-product`, `after-user-init`, `before-final-validation`에 test-only failure를 주입했다. 각 지점을 absent target과 marker·unknown file이 있는 existing target에서 실행했다.

## Expected

모든 injected failure 뒤 target은 설치 전 tree와 동일하고 unknown content는 남는다.

## Result

Pass. Absent target은 모든 failure 뒤 다시 absent가 됐다. Existing target은 marker, unknown file, byte hash와 permission을 포함한 전체 tree가 설치 전과 같았다.

## Evidence

- Stable error: `E_INJECTED_FAILURE`
- 4 points × fresh/existing = 8 rollback cases
- Product directory rollback은 expected product file 외의 file이나 symlink를 발견하면 directory 삭제를 거부한다.

## Decision

Rollback은 이번 실행이 기록한 경로만 역순으로 정리한다. User directory는 비어 있을 때만, product directory는 staged manifest로 소유가 확인될 때만 제거한다.
