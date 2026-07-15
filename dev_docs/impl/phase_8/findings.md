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
