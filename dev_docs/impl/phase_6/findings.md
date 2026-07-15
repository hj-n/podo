# Phase 6 Findings

Phase 6 실험 결과와 배포 limitation을 기록한다.

## Confirmed

- Release archives are byte-reproducible from the same source tree and source commit.
- Distribution identity connects semantic version, Git tag, source commit, compatible Workspace versions, asset names and SHA-256.
- Product templates are valid release content, while instantiated user configuration and Context are excluded.
