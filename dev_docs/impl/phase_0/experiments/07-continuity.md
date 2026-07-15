# Experiment 07 — Cross-task Continuity

## Question

별개의 새 Codex 작업이 State-first 순서로 이전 합성 논의를 이어갈 수 있는가?

## Setup

The captured synthetic Event was connected to:

- `deltas/2026/07/2026-07-15_124500-synthetic-picnic.md`
- `state/synthetic-picnic.md`

State contained a current meeting decision and this dated TODO:

`Mina brings the green umbrella. Created: 2026-07-15. Due: 2026-07-19.`

The context restore policy required State-first reading and allowed Delta or Event only when State was insufficient. A completely separate Codex task received only:

`이전 논의를 이어가자. 현재 결정과 TODO를 간결하게 알려줘.`

User-owned file hashes were captured before the task, after the task, and after another new task containing only `고마워.`

## Expected

새 작업이 현재 결정과 날짜가 있는 TODO를 복원하고, 근거가 필요할 때만 Delta와 Event를 읽으며, No Delta인 경우 파일을 수정하지 않는다.

## Result

Pass on the tested CLI runtime.

The new task restored:

- Riverside Garden at 10:00 on 2026-07-20
- Mina's green umbrella as the meeting marker
- The umbrella TODO due on 2026-07-19

The response did not need the user to repeat the picnic details. The follow-up thank-you created no Context change.

## Evidence

- Trace first read `user_config.md` and `context_restore.md`.
- It searched `state/` and read `state/synthetic-picnic.md`.
- No command read Delta or Event contents.
- Hashes of `user_config.md`, `events/`, `deltas/` and `state/` were identical before and after context restoration.
- The same hashes remained identical after the no-delta task.

## Decision

State-first cross-task continuity is feasible with ordinary readable files and a small routing policy. State must carry current decisions, dated TODOs and trace links so most continuation requests do not need historical reads. Preserve `No Delta → No Update` as an explicit policy and test invariant.
