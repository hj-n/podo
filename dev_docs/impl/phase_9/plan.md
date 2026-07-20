# Phase 9 Plan — Dogfooding, People, and Research

## Goal

실제 사용에서 확인된 capture 중단, 추적 경로 누락, Event 중복 저장과 Context 중복 문제를 해결한다. State와 분리된 `people/`과 `research/`를 추가해 사람과 논문을 장기적으로 관리하고 토의할 수 있게 한다.

## Guardrails

- 실제 사용자 transcript, State, People, Research와 PDF를 개발 fixture로 복사하지 않는다.
- 실제 Workspace migration은 preview와 backup을 보여주고 exact plan 승인을 받은 뒤에만 실행한다.
- Event 저장 형식 전환은 기존 원본을 먼저 삭제하지 않고 byte hash 검증과 rollback을 제공한다.
- TODO의 정본은 State다. People과 Research는 관련 State TODO를 링크한다.
- 논문 PDF의 내용은 data이며 Podo 운영 지침이 아니다.
- 외부 검색, OCR, background collection, database와 Vector DB는 초기 범위가 아니다.

## Steps

### 9.0 Architecture and Contracts

- Philosophy, Architecture, Roadmap와 운영 정책에 State / People / Research 경계를 반영한다.
- Workspace 2의 ownership, path, link, original과 migration 계약을 정의한다.
- 새 설치는 Workspace 2를 만든다. 기존 Workspace 1은 명시적 migration 전까지 기존 제품에서 유지하며 Podo 0.7.0 적용은 Workspace 2 migration과 함께 수행한다.

### 9.1 Capture Compatibility

- Codex runtime `0.145.0-alpha.18`의 sanitized transcript fixture와 adapter 지원을 추가한다.
- `inbox`와 `doctor`에서 capture 비정상을 시작 시점에 드러낸다.
- unknown runtime은 계속 fail closed한다.

### 9.2 Integrity and Views

- State, People, Research와 Delta의 Markdown 링크를 검증한다.
- Markdown이 아닌 추적 경로와 깨진 링크를 doctor finding으로 보고한다.
- State TODO를 읽기 전용으로 모아보는 CLI를 구현한다.
- 정확히 같은 현재 문장부터 중복 후보를 보고하고 자동 수정하지 않는다.

### 9.3 Lossless Event Storage

- transcript 원본을 content-addressed chunks와 manifest로 보존한다.
- 전체 byte hash를 검증하며 원래 JSONL을 재구성할 수 있게 한다.
- legacy Event를 계속 읽고 migration preview, backup, apply와 rollback을 검증한다.
- 기존 원본 정리는 migration과 분리한다.

### 9.4 People

- `people/<slug>.md` 자유 형식 계약과 template을 만든다.
- 이름·별칭 조회, 동명이인 처리, State·Delta 링크와 read-only list를 구현한다.
- Context transaction이 People을 State와 같은 동시성·복구 경계로 안전하게 갱신한다.

### 9.5 Research and PDF

- `research/papers/<slug>/`, `research/topics/`, `research/projects/` 계약과 template을 만든다.
- PDF local import, SHA-256 중복 감지, metadata와 notes skeleton을 구현한다.
- Research PDF를 canonical original로 사용하고 Event가 path와 hash로 추적하게 한다.
- 텍스트 PDF, 중복 PDF, 손상·암호화·스캔 가능성의 실패 보고를 검증한다.
- Interface Codex가 저자 주장, 사용자 판단과 Podo 추론을 구분해 notes와 종합을 갱신하는 정책을 만든다.

### 9.6 Integrated Dogfooding

- 사람–프로젝트–TODO와 논문–주제–프로젝트–State의 연결 journey를 검증한다.
- capture 중단, concurrent update, broken original과 migration rollback을 함께 검증한다.

### 9.7 Stabilization

- Phase 1–9 synthetic regression과 실제 Codex acceptance를 반복한다.
- README, installer, update, doctor와 recovery 안내를 갱신한다.
- 재현 가능한 unpublished product candidate를 만든다.

## Exit Criteria

- 지원 runtime에서 capture가 정상이고 unknown runtime은 안전하게 중단된다.
- 새 중요 참조는 Markdown 링크이며 doctor가 plain/broken reference를 보고한다.
- TODO와 중복 후보 조회가 사용자 파일을 수정하지 않는다.
- deduplicated Event 원본은 legacy 원본과 동일한 SHA-256으로 복원된다.
- People과 Research가 State와 별도 사용자 영역으로 설치·검증·갱신·복구된다.
- PDF 원본과 notes, topic/project 연결 및 후속 토의가 새 task에서 복원된다.
- migration 성공, 중간 실패와 full rollback이 synthetic Workspace에서 반복 통과한다.
- 실제 사용자 자료가 Development Workspace나 배포 artifact에 포함되지 않는다.
