# Podo Templates

이 디렉터리의 파일은 User Workspace 데이터의 초기 형식이다. `{{UPPER_SNAKE_CASE}}` token은 fixture 조립기나 이후 installer가 실제 값으로 바꾼다.

- `workspace/`: 처음 한 번 생성되는 사용자 소유 파일
- `event/metadata.md`: Event의 source와 immutable original 진입점
- `delta.md`: Event로 인해 실제로 달라진 내용
- `state.md`: 자유로운 현재 Context와 날짜가 있는 TODO의 시작 형식

템플릿은 분류 체계를 강제하지 않는다. State는 사용자의 주제에 맞게 자유롭게 구성하며 validator는 계약상 필요한 field, link와 TODO 날짜만 확인한다.
