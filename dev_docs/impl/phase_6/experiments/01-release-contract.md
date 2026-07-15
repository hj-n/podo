# Experiment 01 — Release Contract

## Question

Release asset, version, checksum과 installed manifest를 하나의 검증 가능한 identity로 연결할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- `distribution.json` fixes the public repository, versioned asset names, archive root, required product entries, SHA-256 and no-link/no-user-Context rules.
- Internal archive metadata and external `release.json` share version, tag, repository, source commit, Workspace compatibility, asset names and release notes.
- External metadata additionally records the exact archive SHA-256 used by install manifests.
