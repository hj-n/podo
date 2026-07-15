# Phase 6 Findings

Phase 6 실험 결과와 배포 limitation을 기록한다.

## Confirmed

- Release archives are byte-reproducible from the same source tree and source commit.
- Distribution identity connects semantic version, Git tag, source commit, compatible Workspace versions, asset names and SHA-256.
- Product templates are valid release content, while instantiated user configuration and Context are excluded.
- A verified extracted package can install independently of the development repository and preserve pre-existing valid user files byte-for-byte.
- Fresh package installation rolls back every created product/user initialization path on injected failure.
- Product update and downgrade use the same three-root transaction and preserve user-owned content/mode.
- Every handled replacement failure restores the previous product manifest and bytes before returning an error.
- Product drift, unfinished Context recovery and Workspace incompatibility are preflight blockers, not implicit overwrite or migration approval.
- The update CLI verifies three copies of release identity: GitHub/local registry selection, external metadata/checksum and internal archive metadata.
- Even a correctly checksummed archive cannot use absolute paths, traversal, links or special entries.
