# Experiment 07 — Phase 8 Final Gate

## Question

Phase 8의 connected journeys가 이전 Phase의 세부 failure boundary를 깨지 않고 반복되며, 실제 Codex·candidate·public Release와 cleanup 경계를 모두 만족해 dogfooding으로 진행할 수 있는가?

## Setup

- Source commit: `28c39e93627afc7826e06f6e0d8847702ffbf691`
- `python3 tests/run_phase8_regression.py`
- Final clean `python3 tests/run_phase8_codex_acceptance.py` result
- 모든 tracked Python/JSON과 shell syntax, `git diff --check`, `git fsck --full`
- 같은 source commit에서 0.6.0 candidate 두 번 build
- GitHub public latest와 Desktop/temporary artifact inspection

## Result

Passed on 2026-07-15.

### Phase 1–8 regression

10개 top-level program이 모두 통과했다.

- Phase 1 contract와 9개 corruption case
- Phase 2 fresh/existing install, collision과 모든 install rollback boundary
- Phase 3 transcript capture, Event→Delta→State, No Delta와 failure safety
- Phase 4 defer/resolve, sensitive discard와 TODO lifecycle
- Phase 5 transaction/concurrency/doctor/recovery 전체 suite
- Phase 6 reproducible package, install/update/rollback/download/bootstrap suite
- Phase 7 migration planning/apply/failure/multi-hop/full-rollback/CLI suite
- Phase 8 세 connected journey를 각각 두 clean Workspace에서 반복하고 controlled-failure cleanup 확인

### Real Codex

- Final clean 16-task run이 9개 integrated step을 통과했다.
- Personalization, Context, No Delta, conflict/TODO, recovery diagnosis/apply, compatible update, update/migration separation, migration review/apply, full rollback과 post-rollback State-first restore를 같은 Workspace에서 확인했다.
- Exact command, plan, version, hash, journal과 backup evidence를 응답 marker와 함께 검사했다.
- Marker-owned Desktop container와 isolated Codex home이 제거됐다.

### Static and candidate gate

- 51개 tracked Python/extensionless Python entrypoint가 compile됐다.
- 13개 tracked JSON file이 parse됐다.
- Tracked shell 대상의 syntax와 `git diff --check`가 통과했다.
- `git fsck --full`은 object connectivity error 없이 종료됐다. Reachable history와 무관한 dangling development objects는 삭제하지 않았다.
- Source commit에서 두 0.6.0 archive가 byte-identical했다.
- Candidate SHA-256: `a1c6c47b291f9b20be0a449285f0aa609a75a7d74ebcffe0fd488cb2534bad03`
- Candidate는 Workspace 1만 선언했고 실제 1→2 migration이나 user Event·Delta·State를 포함하지 않았다.

### Public boundary and cleanup

- Public latest는 계속 `v0.5.3`이며 `install.sh`, archive, checksum과 `release.json` 네 asset을 가진다.
- Public `v0.6.0` Release는 존재하지 않는다.
- Desktop Phase 8 test container와 `/tmp` Phase 8 artifact가 남지 않았다.
- Local HEAD와 `origin/main`이 일치했다.

## Decision

Phase 8 exit criteria are met. Podo의 infrastructure와 실제 Codex 사용자 흐름은 synthetic data에서 dogfooding으로 진행할 수 있다. 실제 개인 Workspace 사용, 실제 Workspace format 2 채택과 public v0.6.0 publication은 이 GO에 포함되지 않는다.
