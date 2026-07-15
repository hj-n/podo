# Experiment 02 — Failure Injection

## Question

모든 commit 경계에서 중단해도 기존 State와 recovery evidence를 보존하는가?

## Status

Passed for Context apply boundaries; resolution receipt boundary remains in recovery suite.

## Setup

다음 지점에 test-only failure를 주입했다.

- prepared 이후
- Event 이후
- 첫 Delta 이후
- State 직전과 직후
- 첫 receipt 이후
- 최종 validation 직전과 직후

## Result

- 모든 중단에서 journal은 `recovery-required`와 exact failure point를 남겼다.
- staged Event, Delta, State, receipt와 기존 State bytes가 보존됐다.
- 현재 State는 이전 hash 또는 완전히 준비된 새 hash 중 하나였고 알 수 없는 중간 bytes는 없었다.
- 첫 receipt 이후 중단된 capture를 다시 apply하면 `already-processed`가 아니라 `E_TRANSACTION_PENDING`으로 중단했다.

## Evidence

```text
python3 tests/run_phase5_transactions.py
PASS after-prepared leaves journal, staged bytes and a known State version
PASS after-event leaves journal, staged bytes and a known State version
PASS after-delta-1 leaves journal, staged bytes and a known State version
PASS before-states leaves journal, staged bytes and a known State version
PASS after-state-1 leaves journal, staged bytes and a known State version
PASS after-receipt-1 leaves journal, staged bytes and a known State version
PASS before-final-validation leaves journal, staged bytes and a known State version
PASS after-final-validation leaves journal, staged bytes and a known State version
```

## Decision

중단 증거를 rollback 과정에서 지우지 않는다. Recovery가 plan, journal, staged와 기존 State bytes를 비교해 완료 여부를 판단한다.
