# Phase 4 Findings

## Confirmed

1. `context apply`는 confirmed 변화만 current State에 반영하고 inference와 needs-confirmation을 거부할 수 있다.
2. 확인이 필요한 capture는 permanent Context를 바꾸지 않고 `.podo-work/deferred/`에 한 번만 보류할 수 있다.
3. Deferred는 일반 pending과 분리되어 무관한 새 task마다 같은 질문을 반복 처리하지 않는다.
4. Confirmed resolution Event는 confirmation turn을 주 original로, deferred turn을 related original로 byte 그대로 보존한다.
5. 미래 Context에 중요하지 않은 rejection은 두 capture를 receipt로 닫고 Event, Delta와 State를 만들지 않는다.
6. 모호한 충돌은 기존 State를 보존하고, 명확한 정정은 이전 결론과 새 결론을 Delta에 남긴다.
7. TODO는 Created, 선택적 Due, Completed 또는 Cancelled, Reopened와 Result lifecycle을 검증할 수 있다.
8. 두 State 사이에서 위치가 불명확한 자연어 TODO는 조기 추가되지 않고 사용자에게 high-level 위치 질문을 한다.
9. 사용자의 명확한 State 선택이 exact capture된 뒤 TODO를 올바른 State에 적용할 수 있다.
10. `user_config.md`의 assistant name, personality와 response style이 실제 새 Codex task에 적용된다.
11. Credential로 취급한 capture는 permanent Context로 승격하지 않고 `sensitive-data-excluded` receipt로 정리할 수 있다.
12. 실행 요청이 아닌 synthetic external write를 수행하지 않았고, 마지막 task는 State만 읽어 결정과 완료 TODO를 복원했다.
13. Product 0.3.0은 Workspace 1과 호환되며 기존 사용자 소유 파일을 유지한 채 local install regression을 통과한다.

## Judgment Boundary Learned from Real Codex

채택되지 않은 아이디어와 미래에 다시 확인해야 할 unresolved Context의 경계는 짧은 모호한 표현만으로 항상 같은 결과가 나오지 않는다.

- “좋을지도 모른다, 의견만 달라”는 No Delta가 자연스럽다.
- “다음 task에도 기억해 확인해 달라”는 명시적 지속 의도가 있으므로 defer한다.
- 여러 State 사이 TODO 위치를 물은 직후 현재 prompt에서 사용자가 위치를 답했다면, 이전 질문 capture는 No Delta로 닫고 exact answer capture를 다음 task에서 clear apply하는 것도 안전하다.
- 이미 deferred를 만들었다면 `context resolve`로 두 원본을 연결한다.

따라서 acceptance는 내부 분류 단어를 맞히는지보다 다음 안전 invariant를 검증한다.

1. 확인 전 permanent State가 바뀌지 않는다.
2. 사용자의 명확한 답이 exact capture되기 전에 apply하지 않는다.
3. 적용 후 현재 State와 근거 original이 추적 가능하다.

## Limitations

1. 이전 turn은 다음 task 시작 시 처리되므로 Context 반영은 한 turn 늦다.
2. Production-supported transcript runtime은 여전히 `0.144.0-alpha.4` 하나다.
3. Credential은 Stop hook 시점에 temporary inbox에 먼저 capture될 수 있고 다음 Interface task에서 식별·제외된다. Hook 이전 자동 redaction은 없다.
4. 민감 정보 판단은 현재 Interface Codex policy에 의존한다. 자동 secret scanner를 추가하지 않았다.
5. External boundary는 synthetic no-op sentinel로만 검증했다. 실제 이메일, 일정, 결제나 제3자 시스템은 사용하지 않았다.
6. Multi-file apply와 두 resolution receipt는 각각 atomic write를 사용하지만 전체 transaction의 중단 복구는 Phase 5 범위다.
7. 동시에 여러 task가 같은 State를 바꾸면 stale hash로 중단하며 자동 병합하지 않는다.
8. 실제 개인 데이터, GitHub release, product update와 Workspace migration은 아직 범위 밖이다.

## Phase 5 Handoff

Phase 5는 다음 failure를 우선 다룬다.

- Event·Delta·State 적용 도중 process 중단
- resolution Event 적용 후 한 receipt만 기록된 상태
- capture는 없지만 deferred JSON만 남은 상태 또는 그 반대
- State stale hash와 여러 task의 동시 수정
- 깨진 related original, receipt, Delta와 State link

`podo doctor`는 먼저 읽기 전용으로 문제와 영향 범위를 보여주고, `podo recover`는 기존 State를 추측해 덮어쓰지 않는 승인 기반 복구 계획을 제시해야 한다.
