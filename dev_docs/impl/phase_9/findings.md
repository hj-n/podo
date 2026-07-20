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
