# Phase 4 Gate Decision

- Decision: GO
- Decided: 2026-07-15
- Evidence: `experiments/`, `findings.md`, Phase 1–4 full regression

## Reason

Phase 3의 capture와 writer 위에 clear apply, No Delta, defer, confirmed/rejected resolution, correction과 TODO lifecycle을 구현했다. Synthetic suite는 정상 경로와 invalid, partial, stale, inference, sensitive exclusion 실패 경로에서 기존 permanent Context 보존을 확인했다.

실제 Codex task 15개에서는 user configuration, 명확한 결정, 미확정 충돌 보존, 한 번만 defer, 후속 confirmation, related original, Alpha/Beta TODO 위치, 완료 결과, credential 제외, external no-op와 State-first continuity가 이어서 통과했다. 최종 gate에서 Phase 1 계약, Phase 2 설치와 실제 Codex, Phase 3 capture/context/실제 continuity 및 Phase 4 suite를 다시 실행했다. 모든 marker-owned Desktop artifact는 제거됐다.

## Conditions

- 미채택 proposal은 No Delta로 처리한다. 사용자가 다음 task에도 기억해 확인해 달라고 명시한 unresolved Context는 defer한다.
- 사용자의 명확한 답이 exact capture되기 전에는 permanent State를 바꾸지 않는다.
- Credential은 다음 Interface task에서 제외되기 전까지 temporary inbox에 존재할 수 있음을 privacy 안내에서 숨기지 않는다.
- `0.144.0-alpha.4` 외 runtime은 계속 fail closed한다.
- Concurrent merge, interrupted multi-file transaction, doctor와 recover는 Phase 5 전에는 지원한다고 표시하지 않는다.
- 실제 외부 시스템과 실제 개인 데이터는 이번 gate의 evidence가 아니다.

## Next Phase

Phase 5 — Safe Updates, Doctor, and Recovery.
