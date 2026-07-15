# Experiment 08 — GitHub Releases

## Question

공개 GitHub Release를 인증 없이 설치하고 실제 Release 사이를 update와 rollback할 수 있는가?

## Setup

- public repository: `hj-n/podo`
- immutable Releases: v0.5.0, v0.5.1, v0.5.2, v0.5.3
- baseline install: v0.5.2 `install.sh`
- latest target: v0.5.3
- exact rollback target: v0.5.2
- marker-owned disposable Desktop Workspace

## Expected

- 각 asset은 인증 없이 다운로드된다.
- published archive는 대응 local candidate의 SHA-256과 일치한다.
- latest update와 exact rollback이 모두 성공한다.
- 사용자 소유 sentinel의 content와 mode가 유지된다.
- 테스트가 만든 Desktop 자료가 모두 삭제된다.

## Result

Passed on 2026-07-15.

- v0.5.0 archive: `b8f1496e87e6dcf52d316eced24dfce7770a0266b35c80b3ec88d5096a42a3ba`
- v0.5.2 archive: `c9701b60c84e88979c9d3d6689439a2fdcf0feafbf831692177f4fd375a3a7ad`
- v0.5.3 archive: `6292aadd2f8d34ce232e7fea0d6007f4b73c445bd1948096dfea65756cbcfe06`
- v0.5.0 anonymous fresh install passed.
- v0.5.0의 Python `urllib` downloader는 대상 macOS의 CA store 차이로 쓰기 전에 실패했다. v0.5.2에서 system `curl` transport로 교체했다.
- v0.5.2 anonymous install → latest v0.5.3 update → exact v0.5.2 rollback이 통과했다.
- `user_config.md`, `.podo-work/`, `.podo-backups/`, `state/` sentinel의 hash와 mode가 왕복 전후 동일했다.

## Evidence

- `python3 tests/run_phase6_public_update.py`
- GitHub latest API가 v0.5.3과 네 asset을 반환했다.
- v0.5.3 tag source commit: `0f9f19d62fac7443bfa3fdbf272960b0a1c0e00a`

## Decision

Public distribution과 compatible product rollback 경로를 Phase 6 gate에 포함한다. Python framework CA store에는 의존하지 않는다.
