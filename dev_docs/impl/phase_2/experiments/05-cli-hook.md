# Experiment 05 — Installed CLI and Hook Status

## Question

설치된 Podo만으로 version, validation과 hook 상태를 정확히 설명할 수 있는가?

## Setup

Fresh Desktop Workspace를 설치하고 test parent를 cwd로 사용해 설치된 `.podo/bin/podo`를 실행했다. Development Workspace의 `tools/`는 호출하지 않았다.

## Expected

CLI는 임의 cwd에서 동작하고 installed, trust-unverified와 capture-guard를 구분한다.

## Result

Pass. `version`, `validate`와 `hook-status`가 설치된 product만으로 동작했다. Empty Context는 정상이고 synthetic-fixture mode만 missing Event·Delta·State를 요구했다.

## Evidence

- Version: `Podo 0.1.0 (Workspace 1)`
- Default validation: `OK mode=context-present`
- Hook: `hook-installed: yes`
- Trust: `hook-trust: unverified`
- Capture: `capture: guard-not-ready`

## Decision

CLI는 hook 파일 존재, Codex trust와 capture readiness를 별도 상태로 말한다. Local filesystem에서 trust를 추측하거나 자동 승인하지 않는다.
