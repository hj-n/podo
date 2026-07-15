# Experiment 01 — Installation Contract

## Question

Installer가 쓰기 전에 target 상태를 완전히 분류하고 안전한 결과를 결정할 수 있는가?

## Setup

`tools/install_local.py`가 product source를 staging에 조립·검증한 뒤 Desktop target을 preflight하도록 구현했다. 설치 상태는 product root, manifest, file hash·mode, Workspace version, path type과 symlink로 분류했다.

## Expected

Fresh, user-only, same-product, collision, incompatible와 symlink 상태가 고유한 결과로 분류된다.

## Result

Pass. Fresh와 user-only는 설치 대상으로, 같은 manifest와 file set은 verified reinstall로 분류됐다. Partial product, 수정 product, incompatible Workspace, 잘못된 path type과 symlink는 target 적용 전에 실패했다.

## Evidence

- Command: `python3 tests/run_phase2_installation.py`
- Stable errors: `E_PARTIAL_PRODUCT`, `E_PRODUCT_COLLISION`, `E_WORKSPACE_INCOMPATIBLE`, `E_PATH_TYPE`, `E_SYMLINK`
- Test root: `/Users/hj/Desktop/podo-test-workspaces/`

## Decision

Manifest가 local source path, product와 Workspace version, product-owned file hash와 mode를 기록한다. Manifest 자체는 self-hash하지 않으며, reinstall 때 manifest 내용과 현재 local source의 expected file set을 함께 비교한다.
