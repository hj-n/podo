# Phase 9 Findings

## 9.0 Architecture and Contracts

- People과 Research는 State subtype이 아니라 별도 사용자 소유 영역으로 합의되었다.
- 핵심 흐름은 `Event → Delta → State / People / Research`로 확장되었다.
- Research PDF는 Research가 정본을 소유하고 Event는 path와 SHA-256으로 참조한다.

## 9.1 Capture Compatibility

- Sanitized `0.145.0-alpha.18` fixture가 기존 record family와 turn span 계약을 통과했다.
- `inbox --json`은 매 task 시작 시 `capture_health`를 제공한다.
- 지원 runtime capture 후 health는 `ready`, 최초 설치 상태는 `not-diagnosed`로 구분된다.
- 기존 `0.144.0-alpha.4`, mismatch, unknown runtime, malformed와 partial capture 회귀가 통과했다.

## 9.2 Integrity and Views

- `podo todos`는 State가 소유한 TODO를 due, State와 lifecycle로 읽기 전용 조회한다.
- `Due`는 실제 deadline filter이고 자유로운 `Target`은 별도 표시하여 의미를 합치지 않는다.
- `podo duplicates`와 doctor는 서로 다른 현재 문서의 정확히 같은 문장을 warning 후보로 보고한다.
- 일반 텍스트 추적 경로는 `E_PLAIN_REFERENCE`로 진단하고 기존 Markdown link는 오탐하지 않는다.
- Phase 4 TODO lifecycle과 Phase 1 contract regression이 새 view와 진단 뒤에도 통과했다.
