# Product Scripts

이 디렉터리는 설치된 Podo가 사용하는 local entrypoint를 위한 자리다.

`capture_event`는 현재 hook 입력을 검증한 뒤 `PODO_CAPTURE_NOT_IMPLEMENTED`로 종료하는 fail-closed guard다. Event, Delta 또는 State를 쓰지 않는다. Phase 3에서 versioned transcript adapter와 실제 capture를 구현하기 전에는 `product/.codex/hooks.json`을 설치 가능한 기능으로 공개하지 않는다.
