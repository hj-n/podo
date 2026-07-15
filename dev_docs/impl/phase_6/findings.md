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
- The generated bootstrap preserves quoted Workspace paths and does not create a Workspace before checksum success.
- Product 0.5.0 is the first Release candidate containing the complete Phase 6 package/install/update path for Workspace 1.
- Public v0.5.0 assets are anonymously downloadable and byte-identical to the tagged local candidate.
- Interrupted product update journals now appear separately in doctor and task-startup recovery diagnosis.
- Python framework CA configuration is not reliable enough for the public downloader on the target macOS environment; using the already-required system `curl` avoids that environment-specific trust-store mismatch.
- The failed public download occurred before staging/replacement and demonstrated the existing product preservation boundary.
- Public v0.5.2 can anonymously update to latest v0.5.3 and roll back to exact v0.5.2 while preserving selected user-owned file content and modes.
- The public downloader accepts only API and asset URLs from the expected GitHub repository origins.
- Across three separate real Codex tasks, a non-update request leaves v0.5.2 unchanged, an explicit request uses the canonical update command and reaches v0.5.3, and the next task starts normally without another update.

## Known Limitations

- Workspace format migration is intentionally not part of product update. An incompatible Release stops before writes and is Phase 7 work.
- A handled update failure rolls back automatically, but a process killed between filesystem operations can leave a product journal that doctor reports and later updates refuse to bypass. Automated product-journal recovery is not claimed.
- Historic v0.5.0 and v0.5.1 retain their immutable Python CA-store downloader behavior. Current installations should use latest v0.5.3; v0.5.2 and later use system `curl`.
- Release verification currently relies on GitHub HTTPS, fixed repository origins, metadata identity and published SHA-256. Independent package signing is not implemented.
- Transcript capture remains production-supported only for `codex-cli 0.144.0-alpha.4`.
