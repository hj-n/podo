# Experiment 08 — Critical Edge Cases

## Question

중단, 누락, stale instruction, 중복과 잘못된 source 선택에서 기존 State를 보존하고 실패를 명확히 알리는가?

## Setup

The disposable capture prototype and Interface policy were exercised with explicit failure injection.

| Case | Injection |
|---|---|
| Resume after policy edit | Resume a V1 thread after changing `AGENTS.md` to V2 |
| Missing policy | Temporarily remove the routed schedule policy |
| Missing transcript | Give the adapter a nonexistent source path |
| Wrong task/source | Give the adapter a session ID that differs from `session_meta.id` |
| Duplicate capture | Capture the same session+turn twice |
| Event succeeds, downstream fails | Capture a second Event, then inject exit 42 before Delta/State |
| Damaged existing Event | Change the captured original, then retry the same capture |
| Compaction/interruption | Request App Server compaction for a short synthetic thread and terminate after 75 seconds without completion |

State hashes and Event counts were measured around the failure cases.

## Expected

어떤 실패도 false success나 silent State damage를 만들지 않는다.

## Result

Pass for the safety invariant, with compaction coverage remaining limited.

- Resume loaded current V2 instructions rather than stale V1 instructions.
- Missing policy returned `POLICY_MISSING`.
- Missing transcript returned `CAPTURE_REJECTED|source transcript missing` with exit 1.
- Mismatched session returned `CAPTURE_REJECTED|session identity mismatch` with exit 1.
- Duplicate capture returned `ALREADY_CAPTURED` without adding an Event.
- A second Event could remain as an orphan when simulated Delta/State work exited 42; existing State was unchanged.
- A changed existing original returned `CAPTURE_REJECTED|existing event differs` rather than overwriting it.
- The compaction request did not complete within the test window. After interruption, the original session still had the same 38 records and no partial compaction record.

## Evidence

- State SHA-256 list was identical before and after all injected capture/downstream failures.
- Event count moved from one to two only for the intentionally successful second Event capture.
- The two rejected source cases did not create Event directories.
- The existing-differs case preserved the damaged Event for inspection rather than guessing a repair.
- App Server compaction processes created by the test were terminated; unrelated running app-server processes were identified by cwd and left untouched.

## Decision

The design can fail without silent State damage when it identifies sources by hook session+turn and treats Event snapshots as immutable. An Event without a Delta is recoverable evidence, not a successful Context update; later `doctor` work must report it.

Do not select the newest session file, overwrite a differing Event, or update State after capture failure. Actual post-compaction capture remains an acceptance case for the production adapter because the forced short-thread compaction did not complete in this experiment.
