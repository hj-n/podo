# Product Update Policy

## Explicit Request Only

사용자가 Podo 제품 설치, update 또는 rollback을 명시적으로 요청한 경우에만 제품 명령을 실행한다. 일반 대화, Context update나 새 버전이 있다는 사실만으로 제품 파일을 바꾸지 않는다.

## Canonical Commands

최신 안정 버전은 `./.podo/bin/podo update`, 특정 버전과 migration 없는 rollback은 `./.podo/bin/podo update --version <MAJOR.MINOR.PATCH>`를 사용한다. `AGENTS.md`, `.codex`나 `.podo`를 직접 수정하거나 제품 Git 저장소를 User Workspace에서 clone/pull하지 않는다.

## Stop Conditions

직접 수정된 제품 파일, unfinished Context/product transaction, checksum·Release identity 불일치, unsafe archive 또는 Workspace 비호환이 있으면 덮어쓰기나 migration을 추측하지 않고 중단 이유를 설명한다.

## After Success

Release notes와 설치된 version을 알려준다. Operating Policy나 hook이 바뀌었을 수 있으므로 같은 Workspace에서 새 Codex task를 시작하고 `.codex/hooks.json`을 다시 검토하라고 안내한다. 현재 task가 새 정책을 이미 완전히 적용한다고 가정하지 않는다.
