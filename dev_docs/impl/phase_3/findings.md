# Phase 3 Findings

## Confirmed

1. Stop hook은 exact session, turn과 transcript path를 사용해 다음 작업이 처리할 pending capture를 만들 수 있다.
2. Full session original과 current-turn review view를 분리하면 원본 보존과 중복 없는 의미 판단을 함께 할 수 있다.
3. Interface Codex는 자연어로 명확히 확정된 결정과 TODO를 자유 형식 State request로 만들 수 있다.
4. Product writer는 의미를 분류하지 않으면서 source, hash, date, link, expected State와 apply 순서를 강제할 수 있다.
5. No Delta receipt는 Event·Delta·State를 만들지 않는다.
6. Event 하나가 여러 Delta를 통해 여러 State에 영향을 줄 수 있다.
7. 새 Codex 작업은 State만 읽어 결정과 날짜가 있는 TODO를 복원할 수 있다.
8. Installed Python entrypoint는 bytecode 생성을 막아 실행만으로 product manifest collision을 만들지 않아야 한다.

## Limitations

1. Production-supported transcript runtime은 `0.144.0-alpha.4` 하나다. 다른 runtime은 adapter 추가와 compatibility test가 필요하다.
2. 이전 turn은 다음 Interface 작업 시작 시 처리되므로 Context 반영은 한 turn 늦다.
3. 불확실한 의도, 중요한 충돌과 더 섬세한 apply/confirm 기준은 Phase 4에서 확장한다.
4. 동시에 여러 작업이 같은 State를 바꿀 때 stale hash로 중단하지만 자동 병합은 하지 않는다.
5. 일반 transaction doctor/recover는 Phase 5 범위다.
6. GitHub distribution과 product update는 아직 없다.

## Phase 4 Handoff

Phase 4는 검증된 inbox와 writer를 그대로 사용해 clear change, inference, proposal, conflict와 confirmation의 대화 정책을 확장한다. State schema를 새 category로 고정하지 말고, high-level 사용자 설명과 최소 확인 원칙을 실제 시나리오로 검증해야 한다.
