# Phase 5 Findings

Phase 5 실험 결과를 confirmed evidence와 limitation으로 기록한다.

## Confirmed

- `doctor` is read-only across healthy, interrupted and damaged synthetic Workspaces.
- Unfinished transactions are surfaced at task startup through `recovery_required`; they are not auto-applied or deleted.
- Product drift and user Context damage use distinct finding codes so recovery policy does not mistake one for the other.
- Recovery planning changes only its own plan artifact and pins all evidence, targets and cleanup sources.
- Recovery apply requires an exact safe plan ID, rejects stale pins, is idempotent after success and refuses overlapping State conflicts.
- The two-receipt deferred resolution boundary resumes from its journal without duplicating or skipping a receipt.
- Task startup cannot skip diagnosis: when `recovery_required` is present, inbox includes the read-only doctor result as `recovery_diagnosis`.
- Real Codex tasks preserved baseline State before approval, applied only the exact approved plan and restored the recovered State without permanent history reads.

## Limitations

1. Recovery planner가 자동 적용 후보로 만드는 것은 journaled Context apply transaction뿐이다. 다른 doctor finding은 evidence를 보고하지만 손상 내용을 자동 생성하거나 정리하지 않는다.
2. Defer, No Delta discard와 request 없는 rejected resolution은 기존 atomic write/rollback 경로를 유지한다. 이들은 permanent Event·Delta·State transaction이 아니며 고아 상태는 doctor가 보고한다.
3. `recover` plan 생성은 Context에는 손대지 않지만 사용자 소유 `.podo-work/recovery-plans/`에 plan artifact를 쓴다.
4. Strict merge는 line-based이고 겹침을 보수적으로 manual conflict로 분류한다. TODO나 결정의 의미를 자동 병합하지 않는다.
5. Doctor의 product manifest 진단은 local installer가 만든 verified manifest를 전제로 한다.
6. Failure injection은 `PODO_TEST_FAILURES=1`을 명시한 synthetic test 경로에서만 활성화된다.
7. 실제 개인 데이터, 손상된 원본의 내용 복원과 실제 외부 시스템 재시도는 검증하지 않았다.

## Phase 6 Handoff

- GitHub package와 install/update preflight에서 checksum 검증 뒤 `doctor`의 product/Workspace findings를 활용한다.
- Update는 `PODO_D303_PRODUCT_MODIFIED`를 무시하지 말고 사용자 소유 파일에 쓰기 전에 중단한다.
- Remote package version, checksum과 install manifest의 source identity를 연결한다.
- Update 적용 실패도 product-owned 파일 transaction과 rollback evidence를 남기되, Phase 5의 Context recovery plan과 섞지 않는다.
- README의 GitHub install/update 명령은 실제 release artifact와 end-to-end 검증이 생긴 뒤에만 공개한다.
