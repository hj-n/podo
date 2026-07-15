# Experiment 08 — GitHub Releases

## Question

실제 GitHub Release assets로 fresh install, latest update와 exact rollback을 재현할 수 있는가?

## Status

v0.5.0 and v0.5.1 published; corrected v0.5.2 update/rollback remains pending.

## v0.5.0 Evidence

- Tag `v0.5.0` points to source commit `315a958df60d62ac1a8d8369bb7a34246f538189`.
- GitHub Release contains `podo-0.5.0.tar.gz`, matching checksum, `install.sh` and `release.json`.
- Anonymous re-download SHA-256 `b8f1496e87e6dcf52d316eced24dfce7770a0266b35c80b3ec88d5096a42a3ba` matched the locally built candidate.
- Anonymous latest bootstrap installed a marker-owned Desktop Workspace as GitHub source v0.5.0 and final validation passed.
- Test Workspace/container and local Release build directory were removed.

## Remaining

The first public `podo update` attempt from v0.5.0 stopped before product writes because the macOS framework Python CA store could not verify GitHub. Existing product and user data remained intact and the marker-owned container was removed.

v0.5.2 changes the Release/API transport to the documented system `curl` prerequisite. Publish it, then use public assets for v0.5.1 install → latest v0.5.2 update → exact v0.5.1 rollback.
