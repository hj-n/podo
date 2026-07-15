# Experiment 03 — Context Contracts

## Question

Event, Delta, State, TODO와 user config를 사람이 읽으면서도 검증 가능한 템플릿으로 정의할 수 있는가?

## Setup

Version, Context file과 TODO 규칙을 machine-readable JSON contract로 만들고, 사람이 읽는 Markdown template과 연결했다.

- Product version: `0.1.0`
- Workspace version: `1`
- Event metadata: source, completeness, hash와 original entrypoint
- Delta: Event와 State link, confidence, changed와 why
- State: 자유로운 body와 선택 가능한 section
- TODO: Created 필수, Due 선택, checked TODO의 Completed 필수
- User config: 이름, 성격, 답변 방식과 자유로운 명시 설정

## Expected

템플릿은 자유로운 내용을 허용하면서 source, links, dates와 현재 Context를 추적할 수 있다.

## Result

Pass for contract definition.

모든 계약 JSON은 parse 가능하고 Architecture의 Event → Delta → State 방향을 유지한다. State contract에는 required section이 없으며 `free_form_body`가 true라서 고정 category를 강요하지 않는다.

Event template은 original hash와 completeness를 필수로 두고, Delta template은 Event와 State 양쪽 link를 가진다. User config는 명시적 기본값과 허용된 외부 자료를 자유롭게 적도록 하며 추론한 성향을 자동 확정하지 않는다.

## Evidence

- `.podo/VERSION` and `versions.json` both declare `0.1.0`.
- Workspace template and version contract both declare `1`.
- `context_files.json` has no required State section.
- Event completeness values match the transcript adapter contract.
- All template tokens use `{{UPPER_SNAKE_CASE}}` syntax.

## Decision

Markdown을 canonical user data 형식으로 유지하고 JSON은 형식 자체가 아니라 validator가 읽는 contract로만 사용한다. State 내용과 주제 분류는 자유롭게 두되 source identity, links, dates와 completeness는 명시적으로 검증한다.
