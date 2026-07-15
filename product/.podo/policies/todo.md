# TODO Policy

TODO는 별도 category에 강제로 분류하지 않고 가장 관련 있는 State 안에 기록한다.

- 모든 TODO에는 `Created` 날짜가 필요하다.
- 실제 마감일이 있을 때만 `Due`를 기록한다.
- 완료 시 `Completed`를 기록한다.
- 완료 결과가 이후 Context에 중요할 때 `Result`를 기록한다.

사용자가 TODO 추가를 명시하면 관련 State를 먼저 추론한다. 위치가 분명하면 추가한 뒤 알리고, 여러 State가 비슷하게 관련되거나 새 State가 필요한 경우에만 질문한다.

완료·취소가 현재 결정이나 계획에 영향을 주면 같은 Context update에서 관련 Delta와 State도 검토한다.
