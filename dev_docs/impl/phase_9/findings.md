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

## 9.3 Lossless Event Storage

- Legacy original은 256 KiB content-addressed chunks와 ordered manifest로 전환할 수 있다.
- `event-storage plan`은 source hash를 고정하고 event 수, source bytes, unique chunk bytes와 예상 절감을 먼저 보여준다.
- Exact plan apply 전에 모든 pin을 재검증하고 legacy metadata와 original을 `.podo-backups/`에 보존한다.
- Manifest materialization은 원본과 byte-for-byte 및 SHA-256이 동일했다.
- Rollback은 별도 plan과 pinned current manifest를 요구하고 legacy Event를 복원했다.
- 전환 도중 주입한 실패는 metadata와 original을 기존 bytes로 되돌렸다.

## 9.4 People and Workspace 2

- Podo 0.7.0 candidate는 Workspace 2를 요구하며 새 설치가 `people/`과 세 Research 하위 영역을 만든다.
- Workspace 1→2는 `people`과 `research`만 영향 path로 선언하는 additive migration이다.
- 실제 migration engine의 exact plan, full backup과 staged apply가 기존 State bytes를 보존하며 통과했다.
- `target_kind: people` Context update는 Event와 Delta를 먼저 적용하고 People을 마지막에 갱신한다.
- People alias lookup은 exact name, slug와 alias만 사용하고 ambiguity를 자동 선택하지 않는다.
- People에 TODO checkbox를 복사하려는 update는 거부되어 TODO 정본이 State에 남는다.
- 기존 State transaction과 recovery 회귀가 generic current-document transaction 확장 뒤에도 통과했다.

## 9.5 Research and PDF

- `research import`는 명시적으로 전달된 local PDF의 exact bytes를 Research가 정본으로 소유하게 한다.
- Import는 PDF metadata, 분석 전 notes, PDF를 원본으로 참조하는 Event와 initial Delta를 함께 만든다.
- 같은 SHA-256 PDF는 새 paper나 Event를 만들지 않고 기존 Research path를 반환한다.
- 암호화 PDF와 PDF header가 없는 파일은 내용을 추측하지 않고 거부한다.
- Import 중 Event 뒤에 실패를 주입해도 partial Research, Event와 Delta가 모두 제거되었다.
- 하나의 후속 대화 transaction이 paper notes와 별도 topic을 각각 Delta로 추적하며 갱신했다.
- Paper notes의 `Paper-SHA-256`이 정본 PDF와 다르거나 Research에 TODO checkbox를 두면 validation이 실패한다.
- PDF 내용은 data이고 외부 검색과 OCR은 자동으로 실행하지 않는 정책을 추가했다.

## 9.6 Integrated Dogfooding

- 하나의 synthetic journey에서 State, People, Research project, dated TODO, Markdown link와 lossless Event storage를 함께 검증했다.
- 실제 Codex acceptance는 disposable Workspace에서 사람 소개 → People 복원 → exact PDF import → 사용자 논문 판단·Research project·State TODO 적용 → 새 task 복원을 6개 task로 통과했다.
- 첫 actual acceptance는 Codex가 `{{DELTA_LINK}}`를 plain text로 둬 최종 검증에서 안전하게 중단되는 문제를 발견했다. 현재 문서는 변경되지 않았고 recovery 승인을 요구했다.
- 정책 예제를 `[Delta]({{DELTA_LINK}})`로 명확히 고치고, plain placeholder를 transaction 생성 전에 거부하는 preflight를 추가했다. 해당 실패 회귀와 두 번째 actual acceptance가 모두 통과했다.
- Actual acceptance가 만든 Desktop Workspace와 synthetic PDF는 marker 확인 후 삭제되었다.

## 9.7 Stabilization and Candidate

- `run_phase9_suite.py`의 capture, integrity, Event storage, Workspace migration, People, Research와 통합 journey 7개 program이 통과했다.
- `run_phase9_regression.py`가 Phase 1–8의 10개 program과 Phase 9 suite를 연속 통과했다.
- Phase 6 release builder가 product-only 0.7.0 archive를 두 번 만들고 동일 SHA-256 `824f1313a00e0c9158b64bc7d02ba07edd58eaee5828a00d2dd71ce5c0ed48c1`을 확인했다.
- README는 candidate 상태, Workspace 1→2 migration 경계, People·Research·integrity·Event storage commands와 Phase 9 검증법을 설명한다.
- 0.7.0은 검증된 unpublished candidate다. tag, GitHub Release와 실제 User Workspace migration은 수행하지 않았다.

### Legacy Upgrade Evidence

- 실제 0.6.0 User Workspace의 planner는 미래 사용자 root인 `people`과 `research`를 알지 못해 `E_MIGRATION_IMPACT`로 안전하게 중단됐다. 기존 합성 테스트는 최신 engine으로 옛 Workspace만 흉내 내 이 경계를 놓쳤다.
- 0.6.0과 Workspace 1을 그대로 재현한 새 regression은 첫 plan 실패, Workspace를 바꾸지 않는 compatible bridge update, 0.7.0 exact migration plan과 apply를 실제 설치 CLI 순서로 검증한다.
- 실제 Workspace에는 과거 Podo가 만든 plain Delta path가 남아 있었다. 새 참조는 Context preflight에서 계속 거부하되, 기존 plain path는 update/migration을 막지 않는 read-only doctor warning `PODO_D121_PLAIN_REFERENCE`로 분리했다.
- Bridge update 최종 검증 실패는 제품 0.6.0과 기존 Context를 자동 복원했다. 적용 전후 durable Context aggregate SHA-256은 `b2ecb7dd0644369896f1308f1ad98144d4a13b189ad2747be73e4b01f38d76b9`로 동일했다.
- 호환성 수정 뒤 Phase 1–9 전체 regression이 다시 통과했다.
