# TODO Policy

TODO는 별도 category에 강제로 분류하지 않고 가장 관련 있는 State 안에 기록한다.

## Find the State

다음 순서로 위치를 찾는다.

```text
사용자가 State를 명시함
→ 그 State

현재 대화 주제가 하나로 명확함
→ 현재 주제 State

관련된 기존 State가 하나뿐임
→ 그 State

여러 State가 가능하거나 새 State가 필요함
→ 기존 State를 바꾸지 않고 defer해 위치를 질문
```

“TODO로 추가해줘”, “투두: …” 같은 명시적인 요청 자체가 TODO 생성 승인이다. 위치가 분명하면 생성 여부를 다시 묻지 않는다.

## Dates and Lifecycle

- 모든 TODO에 `Created: YYYY-MM-DD`를 기록한다.
- `Due`는 사용자가 말했거나 확인된 외부 일정에 근거할 때만 기록한다. Podo가 임의로 마감일을 만들지 않는다.
- 상대 날짜가 현재 날짜로 하나의 실제 날짜가 되면 계산해 기록한다. 여러 해석이 가능하면 묻는다.
- 실제 완료를 사용자가 말했거나 결과로 확인했을 때 `[x]`와 `Completed`를 기록한다.
- 취소가 명확하면 `[x]`와 `Cancelled`를 기록한다. 조용히 삭제하지 않는다.
- 완료 또는 취소된 항목을 다시 열면 `[ ]`로 바꾸고 기존 terminal 날짜와 새 `Reopened` 날짜를 함께 남긴다.
- 결과가 이후 Context에 중요하면 `Result`를 기록한다.
- 실행을 시도했다는 이유만으로 완료 처리하지 않는다.

```md
- [ ] 설치 문서를 작성한다.
  - Created: 2026-07-15
  - Due: 2026-07-18

- [x] 설치 문서를 검토한다.
  - Created: 2026-07-15
  - Completed: 2026-07-17
  - Result: 누락된 update 설명을 추가했다.

- [x] 기존 배포를 진행한다.
  - Created: 2026-07-15
  - Cancelled: 2026-07-17
  - Result: 배포 계획을 새 방식으로 바꿨다.
```

Checked TODO는 `Completed` 또는 `Cancelled` 중 정확히 하나를 가진다. terminal 이력이 있는 open TODO는 `Reopened`를 가진다.

## Changes

사용자가 특정 TODO의 완료·취소·마감일 변경을 명확히 요청하면 그 요청 자체가 승인이다. 계획 변경 때문에 여러 TODO가 영향을 받지만 범위가 모호하면 기존 항목을 유지하고 무엇을 바꿀지 확인한다.

완료·취소·재개가 현재 결정이나 계획에 영향을 주면 같은 Context update에서 관련 Delta와 State도 실제 달라진 만큼만 갱신한다.
