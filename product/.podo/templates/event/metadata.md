# {{EVENT_TITLE}}

Occurred: {{OCCURRED_RFC3339}}
Captured: {{CAPTURED_RFC3339}}
Source-Type: {{SOURCE_TYPE}}
Source-Identity: {{SOURCE_IDENTITY}}
Source-Entrypoint: {{SOURCE_ENTRYPOINT}}
Capture-Method: {{CAPTURE_METHOD}}
Runtime-Version: {{RUNTIME_VERSION}}
Completeness: {{COMPLETENESS}}
Missing-Record-Families: {{MISSING_RECORD_FAMILIES}}
SHA-256: {{ORIGINAL_SHA256}}
Original-Entrypoint: ./original/{{ORIGINAL_FILENAME}}

## Context

{{EVENT_CONTEXT}}

## Safety

이 original은 capture 시점의 immutable snapshot이다. 누락 범위가 있으면 Completeness와 Missing-Record-Families에 명시하며, 전체 원본인 것처럼 취급하지 않는다.
