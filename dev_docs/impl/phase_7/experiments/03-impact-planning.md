# Experiment 03 — Migration Discovery and Impact Planning

## Question

Verified target package에서 유일한 migration chain과 exact 영향 path를 찾아 permanent Context 변경 없이 plan을 만들 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- Verified synthetic target Release 1.0.0 declared Workspace 2 and one `1-to-2` migration.
- Planning pinned the current install manifest, Workspace version, State hash/mode and target archive/source identity.
- Repeating the plan with identical evidence returned the same plan ID and file.
- Product, `WORKSPACE_VERSION`, State and user config hashes remained unchanged.
- Missing path, multiple reachable paths, wrong descriptor versions and product/absolute/traversal impact paths failed before plan creation.
- `python3 tests/run_phase7_planning.py`

## Decision

Migration target product version must be exact. A target that already supports the current Workspace belongs to normal `podo update`, while an incompatible target requires one unique declared migration chain.
