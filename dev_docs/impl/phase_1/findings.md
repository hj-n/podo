# Phase 1 Findings

## Confirmed

1. Architecture의 product-owned 경계를 실제 `product/` tree로 표현할 수 있다.
2. 작은 `AGENTS.podo.md`가 새 Codex 작업에서 user config와 State-first policy를 적용한다.
3. Hook, transcript adapter, ownership, version과 Context file 계약을 JSON으로 기계적으로 읽을 수 있다.
4. Event, Delta, State와 user config는 Markdown으로 사람이 읽을 수 있고 template으로 결정적으로 생성된다.
5. State는 고정 section을 요구하지 않으면서 TODO 날짜와 link를 검증할 수 있다.
6. Event original hash, completeness, Delta links와 version compatibility의 주요 손상을 dependency 없이 탐지한다.
7. 합성 Workspace를 두 번 조립해 동일한 결과를 얻으며 local Python cache에 영향받지 않는다.
8. Capture 기능이 없는 현재 단계에서도 hook target은 존재하고 명시적으로 fail-closed하며 State를 수정하지 않는다.

## Limitations

1. `capture_event`는 contract guard이며 실제 transcript adapter나 Event writer가 아니다. Production supported runtime 목록은 의도적으로 비어 있다.
2. App Server fallback은 contract에 `partial`로만 정의됐고 실제 fallback client는 구현하지 않았다.
3. Desktop hook review UI, attachment와 post-compaction capture는 Phase 3 acceptance에 남아 있다.
4. Validator는 파일 계약을 검사하지만 대화의 의미나 Delta 판단이 올바른지는 판정하지 않는다.
5. Installer, update, migration, transaction과 recovery는 현재 범위에 없다.
6. README는 개발 검증만 안내하며 작동하는 install command를 공개하지 않는다.

## Phase 2 Handoff

1. `product/AGENTS.podo.md`를 User Workspace의 `AGENTS.md`로 설치한다.
2. `.codex/hooks.json`과 `.podo/`를 product-owned 단위로 복사한다.
3. `WORKSPACE_VERSION`, user config와 Context directory는 template에서 없을 때만 만든다.
4. 기존 사용자 소유 파일의 hash와 내용을 보존한다.
5. hook 검토·신뢰가 필요한 상태를 사용자가 이해할 수 있게 안내한다.
6. `.podo/bin/podo`와 local install command를 구현하되 capture guard를 capture 성공으로 표시하지 않는다.
7. 설치 결과를 현재 validator로 검사하고 temporary Workspace 생성·제거 흐름을 만든다.
