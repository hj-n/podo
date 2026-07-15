# Phase 0 Findings

Phase 0 used only synthetic data in a disposable Workspace outside this repository. Raw transcripts and temporary prototypes were not committed.

## Confirmed

1. A small User Workspace `AGENTS.md` can establish the Interface role and route to only the relevant `.podo/policies/` file.
2. `user_config.md` can provide the assistant name and personality across separate tasks without being modified.
3. Interface Codex can run a hidden Workspace-local `.podo/bin/podo` entrypoint.
4. A trusted project hook receives exact session, turn, cwd and transcript path at prompt submission and turn stop.
5. App Server can read the hook-identified thread through a supported thread/turn/item protocol.
6. The tested App Server historical read preserves user and assistant messages but not every persisted tool/command record present in local JSONL.
7. A versioned local adapter can snapshot the hook-identified raw transcript, record its hash and source, and avoid duplicate Events.
8. A separate new task can restore current decisions and dated TODOs from State without reading Delta or Event when State is sufficient.
9. No-delta conversations and injected capture failures can leave all user-owned Context hashes unchanged.

## Limitations

1. Official Codex documentation explicitly says the transcript file pointed to by hooks is not a stable interface. The tested parser is valid only for `codex-cli 0.144.0-alpha.4` until another version passes compatibility tests.
2. Project hooks require a trusted `.codex/` config layer and separate trust of the exact hook definition. The experiment used an explicit automation-only hook trust bypass after isolating the Workspace.
3. At the initial gate, Architecture defined only `AGENTS.md` and `.podo/` as product-owned and did not authorize `.codex/hooks.json`. This was the explicit decision required before Phase 1 and is resolved below.
4. The repeatable tests used the CLI binary bundled with Codex desktop. The actual Desktop Local Project hook review UI and end-to-end acceptance still need a manual surface test before installation is considered usable.
5. A forced compaction of the short synthetic thread did not finish within 75 seconds. Interruption was safe, but post-compaction capture was not demonstrated.
6. Attachments were absent from the synthetic transcript. Raw bytes would be preserved when represented in the transcript, but attachment completeness needs a fixture in the production adapter tests.
7. Raw transcripts can include prompts, tool outputs and opaque encrypted reasoning records. They must remain local, inherit User Workspace protection and never be uploaded automatically.

## Architecture Impact

Automatic and correctly identified capture cannot be implemented by `AGENTS.md` plus `.podo/` alone in the tested Desktop-oriented design. The minimal evidence-backed addition is a project-local `.codex/hooks.json` that invokes a product-owned script under `.podo/`.

This changes the product ownership boundary and installation/trust flow. It must be discussed and added to `initial_architecture.md` before Phase 1 treats it as product structure.

Resolution on 2026-07-15: the user approved `.codex/hooks.json` as a product-owned file. Architecture now includes its install, update, trust and health-check boundaries.

The Event identity should be session+turn, not session alone. A session grows on resume; each meaningful captured turn is an immutable snapshot. Capture failure must block Delta and State, while a captured Event followed by downstream failure remains inspectable and recoverable.

App Server remains valuable as a supported partial fallback and validation source. It must not be labeled a full-original fallback unless a future tested version returns all required item families.
