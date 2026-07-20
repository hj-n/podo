# Context Restore Policy

## Read Order

1. 계획·결정·TODO는 `state/`, 사람 중심 맥락은 `people/`, 논문·연구 질문은 `research/`에서 관련 현재 문서를 찾는다.
2. 현재 내용이 어떻게 바뀌었는지 필요할 때만 연결된 Delta를 읽는다.
3. 정확한 원문이나 근거가 필요할 때만 Delta가 연결한 Event Metadata와 original 또는 Research PDF를 읽는다.

```text
State / People / Research → 필요한 경우 Delta → 필요한 경우 Event 또는 PDF
```

전체 Workspace나 모든 과거 Event를 매번 읽지 않는다. 현재 문서만으로 충분하면 과거 기록이나 PDF를 더 열지 않는다.

관련 State를 확실히 찾지 못하면 비슷한 이름을 임의로 현재 Context로 정하지 않는다. 찾은 후보와 부족한 정보를 간결하게 보여주고 필요한 경우에만 사용자에게 묻는다.
