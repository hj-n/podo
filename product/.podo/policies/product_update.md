# Product Update Policy

## Explicit Request Only

사용자가 Podo 제품 설치, update 또는 rollback을 명시적으로 요청한 경우에만 제품 명령을 실행한다. 일반 대화, Context update나 새 버전이 있다는 사실만으로 제품 파일을 바꾸지 않는다.

## Canonical Commands

최신 안정 버전은 `./.podo/bin/podo update`, 특정 버전과 migration 없는 rollback은 `./.podo/bin/podo update --version <MAJOR.MINOR.PATCH>`를 사용한다. `AGENTS.md`, `.codex`나 `.podo`를 직접 수정하거나 제품 Git 저장소를 User Workspace에서 clone/pull하지 않는다.

## Stop Conditions

직접 수정된 제품 파일, unfinished Context/product transaction, checksum·Release identity 불일치, unsafe archive 또는 Workspace 비호환이 있으면 덮어쓰기나 migration을 추측하지 않고 중단 이유를 설명한다.

## Workspace Migration

Target product가 현재 `WORKSPACE_VERSION`을 지원하지 않으면 일반 update를 실행하지 않는다. 사용자가 migration 검토를 요청하면 exact target version으로 `./.podo/bin/podo migrate --version <MAJOR.MINOR.PATCH>`를 실행해 변경 이유, 영향 path, backup 위치와 rollback 조건을 먼저 보여준다.

Plan 생성은 migration 승인이 아니다. 사용자가 표시된 exact plan 적용을 별도로 승인한 경우에만 `./.podo/bin/podo migrate --apply <plan-id>`를 실행한다. Version만 다시 언급하거나 “업데이트해줘”라고 한 요청으로 apply를 추측하지 않는다.

Migration 뒤 full rollback은 현재 사용자 데이터를 덮어쓸 수 있다. `./.podo/bin/podo migrate rollback --backup <backup-id>`로 rollback plan과 migration 이후 변경을 먼저 보여주고, exact rollback plan을 별도로 승인받은 뒤 같은 `migrate --apply <plan-id>` 경로로 실행한다.

Backup은 사용자 소유 `.podo-backups/`에 남는다. 자동 삭제, 외부 전송 또는 사용자의 별도 요청 없는 정리를 하지 않는다.

## After Success

Release notes와 설치된 product/Workspace version, 보존된 backup 위치를 알려준다. Operating Policy나 hook이 바뀌었을 수 있으므로 같은 Workspace에서 새 Codex task를 시작하고 `.codex/hooks.json`을 다시 검토하라고 안내한다. 현재 task가 새 정책을 이미 완전히 적용한다고 가정하지 않는다.
