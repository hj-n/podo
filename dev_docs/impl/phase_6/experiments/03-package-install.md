# Experiment 03 — Package Install

## Question

Checksum을 확인한 package로 빈 Workspace를 설치하고 사용자 소유 경계를 초기화할 수 있는가?

## Status

Passed on 2026-07-15.

## Evidence

- The archive's standalone `install.py` loads the packaged `product_install.py`; it does not depend on the development repository.
- Fresh install writes only the three product roots and creates missing user-owned files/directories once.
- Existing valid `user_config.md` and State bytes plus restrictive file mode remain identical.
- Reinstalling the exact package returns `ALREADY_INSTALLED` after product manifest/hash verification.
- Partial product paths and managed symlinks fail before writes.
- Failure injection after staging, product apply, user initialization and before final validation leaves no partial Workspace.
- Installed manifest version 2 records GitHub/local-release source, tag, source commit, archive SHA-256 and every product file hash/mode.

## Commands

```bash
python3 tests/run_phase6_package_install.py
python3 tests/run_phase2_installation.py
```
