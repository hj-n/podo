# Context Restore Policy

## Read Order

1. 현재 요청과 관련된 `state/` 파일을 찾고 읽는다.
2. 현재 결론이 어떻게 바뀌었는지 필요할 때만 State가 연결한 Delta를 읽는다.
3. 정확한 원문이나 근거가 필요할 때만 Delta가 연결한 Event Metadata와 original을 읽는다.

```text
State → 필요한 경우 Delta → 필요한 경우 Event
```

전체 Workspace나 모든 과거 Event를 매번 읽지 않는다. State만으로 충분하면 과거 기록을 더 열지 않는다.

관련 State를 확실히 찾지 못하면 비슷한 이름을 임의로 현재 Context로 정하지 않는다. 찾은 후보와 부족한 정보를 간결하게 보여주고 필요한 경우에만 사용자에게 묻는다.
