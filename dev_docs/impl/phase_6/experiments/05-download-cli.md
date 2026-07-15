# Experiment 05 — GitHub Download and CLI

## Question

Latest와 exact GitHub Release를 인증 유무에 맞게 조회하고 checksum 검증 뒤 update할 수 있는가?

## Status

Passed against local registry and public GitHub v0.5.0 on 2026-07-15.

## Evidence

- `podo update` selects the local test registry's latest stable Release and `--version` selects an exact semantic version.
- External metadata, checksum filename/value, archive SHA-256 and internal metadata must all agree before extraction.
- A checksum mismatch leaves the current product unchanged.
- A correctly checksummed archive containing traversal is rejected before installer execution and cannot escape the temporary directory.
- Local Release directories are available only when both `PODO_TEST_RELEASES=1` and `PODO_RELEASE_DIR` are present; otherwise the production path is the fixed public `hj-n/podo` GitHub API.
- Successful update/rollback output includes Release notes, new-task guidance and hook review guidance.

- Public v0.5.0 archive downloaded without authentication and matched the local candidate SHA-256 exactly.
- The public bootstrap installed a manifest whose source kind, tag and archive hash identify the GitHub Release.
