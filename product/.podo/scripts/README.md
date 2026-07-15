# Product Scripts

이 디렉터리는 설치된 Podo가 사용하는 local implementation이다. 사용자는 보통 `.podo/bin/podo`만 실행한다.

- `capture_event`: trusted Stop hook의 exact source identity를 받아 pending inbox capture를 atomic하게 만든다.
- `transcript_adapter.py`: 지원 Codex runtime의 session, turn, record family와 completeness를 검증한다.
- `context_store.py`: verified capture를 Event·Delta·State로 적용하거나 No Delta로 처리한다.
- `validate_workspace.py`: installed Workspace의 version, path, link, Event hash와 TODO date를 검사한다.

현재 production-supported transcript runtime은 `0.144.0-alpha.4` 하나다. Unknown runtime을 비슷해 보인다는 이유로 파싱하지 않는다. Hook과 scripts는 transcript나 Context를 Workspace 밖으로 전송하지 않는다.
