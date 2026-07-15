# Phase 8 Findings

Phase 8 통합 실험에서 관찰한 결과와 limitation을 기록한다. 예상 결과를 성공 evidence로 쓰지 않는다.

## Everyday Journey

- Release install 뒤 같은 State를 계속 갱신해도 Event original, Delta link와 optimistic State hash가 유지됐다.
- Personalization은 Context change와 분리할 수 있었고, No Delta 및 deferred conflict도 permanent Context hash를 보존했다.
- Resolution Event 하나가 확인 turn과 보류 turn의 exact originals를 함께 연결하므로 새 결정의 이유를 한 위치에서 추적할 수 있었다.
- TODO의 완료와 취소/재개 lifecycle을 하나의 최종 State에서 함께 표현하고 validator로 확인할 수 있었다.

## Recovery Journey

- 같은 State hash를 기준으로 준비된 요청도 먼저 적용된 요청 이후에는 stale로 거부되어, 긴 사용자 여정에서도 optimistic evidence가 유효했다.
- Transaction이 Event와 Delta 일부를 이미 설치한 뒤 중단되어도 현재 State는 known version으로 남았고 exact recovery가 같은 staged plan을 이어서 완료했다.
- Doctor와 startup은 같은 transaction diagnosis를 공유했지만 planning과 apply는 계속 분리됐다.
- Event original 누락과 State link 손상에는 안전한 자동 복구 의미가 없으므로 `nothing-to-recover`가 올바른 결과였다.

## Product Lifecycle Journey

- Product update와 exact-version rollback을 migration 전후 흐름에 연결해도 user-owned bytes와 mode 경계가 유지됐다.
- Incompatible update가 migration plan까지 대신 만들면 승인 경계가 흐려지지만, 현재 구현은 update 단계에서 artifact 없이 멈췄다.
- 실패한 migration backup과 성공한 migration backup은 별개로 보존되며, 성공 뒤 full rollback은 추가 safety backup을 만들었다.
- Full rollback 뒤 product, Workspace version과 사용자 Context evidence가 모두 baseline과 같아야만 lifecycle이 완료된 것으로 판단할 수 있었다.

## Repeatability and Cleanup

- 세 journey의 stable step shape는 두 clean run에서 같았고, 각 journey가 내부 temporary Workspace를 완전히 소유하므로 순서 의존성이 없었다.
- Event timestamp와 생성된 Delta path를 간접적으로 포함하는 State hash는 내용 검증 evidence지만 cross-run identity로 사용하면 안 된다.
- 실패 summary는 완료된 step과 generic failure type만 남겨 absolute temporary path나 transcript 내용을 노출하지 않을 수 있었다.
- Python context manager cleanup은 성공과 controlled exception 모두에서 temporary Workspace를 제거했다.

## Real Codex End-to-End

- 16개 새 task가 이어져도 `user_config.md` 개인화, pending/deferred lifecycle과 State-first 복원이 유지됐다.
- Recovery-required startup은 누적 pending보다 diagnosis를 우선했고, exact recovery 뒤 다음 task가 pending을 정상 정리할 수 있었다.
- Compatible update, incompatible update rejection, migration과 full rollback을 같은 Context 뒤에 실행해도 승인 경계가 합쳐지지 않았다.
- Non-zero로 정상 거부된 CLI command도 중요한 acceptance evidence이므로 command parser가 성공한 execution만 수집하면 안 된다.
- 자연어 응답의 문장 부호나 고정 표현보다 plan ID, version, affected path, backup 생성 시점과 file evidence가 안정적인 판정 기준이었다.

## Known Limitations

- Product 0.6.0은 unpublished development candidate이며 public latest는 v0.5.3이다.
- 모든 Context와 migration evidence는 synthetic data다. 실제 개인 Workspace나 production Workspace format 2를 사용하지 않았다.
- Synthetic journey는 두 번 반복했지만 final real Codex end-to-end gate는 한 clean run이다. Codex 자연어 표현은 비결정적이므로 구조적 evidence로 판정했다.
- Real acceptance는 현재 macOS bundled Codex CLI, local filesystem과 network authentication에 의존한다. Windows native behavior를 검증하지 않았다.
- Migration entrypoint OS sandbox, encrypted/remote backup, automatic backup retention과 hard-kill automatic recovery는 여전히 제공하거나 검증하지 않는다.
- Backup은 Event original을 포함할 수 있으므로 dogfooding에서도 사용자가 승인 없이 삭제·업로드하거나 개발 저장소로 복사하면 안 된다.
- 통합 테스트 통과는 Podo가 실제 사용에서 Context 복원 비용을 줄인다는 제품 가치의 증거가 아니다. 그 판단은 Phase 9 dogfooding에서 관찰해야 한다.
