# Experiment 06 — Synthetic Decision Suite

## Question

Phase 4 판단 lifecycle의 정상 경로와 주요 실패 경로를 disposable Workspace에서 반복할 수 있는가?

## Status

Passed.

## Setup

Phase 4 decision, TODO suite와 Phase 1–3 contract, capture, context, installer regression을 함께 실행했다.

## Result

- defer, confirmed/rejected resolution, correction, invalid/partial failure가 통과했다.
- TODO lifecycle 정상·실패 경로가 통과했다.
- inference와 sensitive exclusion 경계가 통과했다.
- Phase 1 contract, Phase 2 Desktop installation과 rollback, Phase 3 capture/context suite가 통과했다.
- Desktop installer artifact는 marker 확인 후 정리됐다.

## Evidence

```text
python3 tests/run_phase4_decisions.py
python3 tests/run_phase4_todo.py
python3 tests/run_phase3_capture.py
python3 tests/run_phase3_context.py
python3 tests/run_phase2_installation.py
python3 tests/run_phase1_contracts.py
```

## Decision

Synthetic gate는 통과했다. 실제 Codex가 같은 정책을 자연어에서 일관되게 수행하는지 Experiment 07로 진행한다.
