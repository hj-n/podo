# Experiment 03 — Policy, Config, and Command

## Question

작은 `AGENTS.md`가 필요한 상세 정책과 사용자 설정만 읽고 Workspace 내부 명령을 실행할 수 있는가?

## Setup

The root `AGENTS.md` routed schedule requests to `.podo/policies/schedule.md` and TODO requests to `.podo/policies/todo.md`. Each file had a distinct synthetic marker.

Four independent tasks were run:

1. Ask for the schedule marker.
2. Ask for the TODO marker.
3. Ask Codex to execute `.podo/bin/podo`.
4. Temporarily rename the required schedule policy and ask for its marker.

The SHA-256 of `user_config.md` was recorded before and after all tasks.

## Expected

관련 policy marker와 user config가 적용되고, 무관한 policy는 사용되지 않으며, 필수 policy 누락 시 안전하게 중단한다.

## Result

Pass on the tested CLI runtime.

- Schedule task returned `SCHEDULE_POLICY_V1`.
- TODO task returned `TODO_POLICY_V1`.
- Local entrypoint returned `PODO_COMMAND_OK|synthetic-workspace`.
- Missing schedule policy returned `POLICY_MISSING` rather than inventing a marker.
- `user_config.md` had the same SHA-256 before and after.

## Evidence

- Schedule trace command read `user_config.md` and `schedule.md`; it did not mention `todo.md`.
- TODO trace command read `user_config.md` and `todo.md`; it did not mention `schedule.md`.
- Command trace executed the hidden Workspace entrypoint successfully.
- The missing-policy trace attempted the routed file and reported the explicit failure marker.

## Decision

Keep `AGENTS.md` as a small router and place detailed behavior in `.podo/policies/`. Policy files must have explicit missing-file behavior. `user_config.md` remains user-owned and read-only unless the user directly requests a change. A Workspace-local `.podo/bin/podo` entrypoint is executable by Interface Codex.
