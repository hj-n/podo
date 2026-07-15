# Experiment 03 — Existing Data and Collisions

## Question

Existing user data를 보존하면서 product collision, incompatible version과 symlink를 차단하는가?

## Setup

Valid existing `user_config.md`, `WORKSPACE_VERSION`과 unknown note를 서로 다른 permission으로 만들었다. 별도 case에서 partial AGENTS, 설치 후 수정한 AGENTS, Workspace version 2, managed symlink와 file/directory mismatch를 주입했다.

## Expected

User-owned bytes와 permission은 유지되고 각 collision은 쓰기 전에 고유한 error code로 실패한다.

## Result

Pass. Existing user files의 byte hash와 permission이 모두 유지됐다. 다섯 preflight failure는 target tree를 바꾸지 않았다.

## Evidence

- Preserved modes: user config `0600`, Workspace version `0640`, unknown note `0600`
- Failure cases: partial product, modified product, incompatible Workspace, managed symlink, path type mismatch
- 모든 case에서 failure 전후 tree snapshot 일치

## Decision

Create-once 경로는 누락된 경우만 만들고 기존 byte나 permission을 정규화하지 않는다. Product 상태를 증명할 manifest가 없으면 내용을 추측하거나 덮어쓰지 않는다.
