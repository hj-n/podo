# Experiment 05 — Template Assembly Gate

## Question

Phase 1 산출물만으로 동일한 synthetic User Workspace를 반복 생성하고 검증할 수 있는가?

## Setup

README에 기록한 canonical command로 저장소 밖의 empty temporary directory에 synthetic Workspace를 조립하고 validator를 실행했다. 전체 contract test는 별도의 두 Workspace를 조립해 파일 tree digest를 비교하고 9개 손상 fixture를 검증했다.

Python cache가 없는 상태와 `py_compile` 후 cache가 있는 상태에서 전체 suite를 다시 실행해 조립 결과가 local build artifact에 의존하지 않는지도 비교했다.

## Expected

두 disposable Workspace의 계약 대상 파일이 동일하고 validator를 통과한다.

## Result

Pass.

- README의 build와 validate command가 그대로 실행됐다.
- 두 Workspace는 같은 파일 tree와 digest를 가졌다.
- Valid Workspace 두 개가 모두 통과했다.
- 9개 failure case가 기대 code로 실패했다.
- Capture guard는 명시적 미구현 오류를 내고 어떤 파일도 수정하지 않았다.
- `__pycache__` 유무가 조립 결과에 영향을 주지 않았다.

## Evidence

- `BUILT /private/tmp/podo-phase1-...`
- `OK /private/tmp/podo-phase1-...`
- Deterministic digest: `38d36ec7fc3d0573ce905b261ba7d41f10a226ccee5387a952fd23a406038e58`
- `PASS valid-workspace 9 failure cases`
- `CACHE_INDEPENDENT=yes`
- `git diff --check` passed.

## Decision

Phase 1 exit criteria를 충족했다. Builder는 개발 전용으로 유지하고 installer처럼 공개하지 않는다. Phase 2는 같은 product tree와 templates를 사용해 create-once 보호를 갖춘 실제 local installation loop를 구현한다.
