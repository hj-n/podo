# Phase 0 Gate Decision

- Decision: CONDITIONAL GO
- Decided: 2026-07-15
- Evidence: `experiments/` and `findings.md`

## Reason

Phase 0's essential user outcome was reproduced: one synthetic Codex conversation became an identifiable, hashed Event, and a separate new task continued from the resulting State and dated TODO without the user repeating the context.

Instruction routing, user configuration, local command execution, Event idempotency, State-first reads and failure safety all worked. The remaining risk is not whether capture is possible, but that complete Desktop capture currently depends on a trusted project hook and a version-dependent local transcript adapter.

## Conditions or Required Changes

Before Phase 1 implementation proceeds:

1. **Resolved 2026-07-15:** `.codex/hooks.json` is approved as a product-owned file and Architecture has been updated.
2. Define a transcript adapter interface keyed by exact Codex runtime version.
3. Unknown schemas, missing required record families and identity mismatches must fail closed or be labeled `partial`; they must never update State as if capture succeeded.
4. Use App Server `thread/read` as a supported partial fallback and source cross-check, not as full-original capture on the evidence currently available.
5. Add a Desktop Local Project acceptance scenario covering hook review/trust, one real synthetic turn, attachment representation and post-compaction capture.
6. Document in README that installation activates a reviewed local hook and that raw Events may contain sensitive conversation and tool content.

## Next Phase

Phase 0 is complete and the Architecture condition is resolved. Phase 1 may begin. Conditions 2–6 become explicit Phase 1 contracts and acceptance tests rather than hidden implementation assumptions.
