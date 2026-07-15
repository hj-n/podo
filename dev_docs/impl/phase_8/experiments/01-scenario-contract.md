# Experiment 01 — Scenario and Evidence Contract

## Question

Phase별 성공 메시지를 다시 실행하는 것만으로 충분한가, 아니면 하나의 사용자 여정에서 실제 상태 전이와 승인 경계를 별도로 고정해야 하는가?

## Setup

Architecture의 설치, Context, 판단, TODO, recovery, update와 migration 약속을 Phase 1–7의 canonical command 및 test evidence와 대조했다. 실제 개인 데이터나 실제 Workspace format 2는 범위에 넣지 않았다.

## Result

개별 Phase suite는 각 기능의 정상·실패 경계를 깊게 검증하지만, 앞 단계가 만든 실제 State와 receipt를 뒤 단계가 계속 사용하는 전체 여정은 별도 계약이 필요하다. Phase 8은 다음 세 journey를 독립적인 새 Workspace에서 실행한다.

| Journey | 시작 | 핵심 전이 | 종료 evidence |
|---|---|---|---|
| everyday | 빈 directory | install → personalize → Context → conflict → TODO | valid Event·Delta·State와 clean inbox |
| recovery | valid Context | stale reject → interrupted transaction → diagnosis → approved recover | preserved prior State와 committed recovery receipt |
| product | Workspace 1 Context | update/rollback → incompatible reject → migration failure/success → full rollback | original product·data와 retained backups |

## Evidence Ledger

각 step은 최소한 다음 값을 기록한다.

- `id`: journey 안에서 유일하고 순서가 고정된 step ID
- `architecture`: 검증하는 Architecture section
- `outcome`: `passed` 또는 `failed`
- `evidence`: version, path, hash, receipt, finding, plan, backup 또는 command처럼 결과를 독립적으로 확인한 짧은 항목

한 run의 summary는 다음 envelope을 사용한다.

```json
{
  "schema_version": 1,
  "phase": 8,
  "journey": "everyday | recovery | product",
  "run_id": "caller-supplied disposable run ID",
  "status": "passed | failed",
  "steps": [
    {
      "id": "stable-step-id",
      "architecture": ["3", "5"],
      "outcome": "passed",
      "evidence": ["human-readable verified fact"]
    }
  ]
}
```

Summary에는 Workspace absolute path, transcript 원문, credential, 사용자 데이터 또는 시각에 따라 달라지는 내부 temporary path를 넣지 않는다. 실패 시에도 완료된 step과 실패 step을 출력하되, summary 자체를 성공 증거로 간주하지 않고 assertion이 확인한 underlying files를 근거로 삼는다.

## Decision

세 journey는 공통 evidence ledger를 사용하지만 서로의 임시 Workspace를 재사용하지 않는다. Canonical suite가 각 journey를 두 번 실행하고 stable step ID 및 최종 status가 같은지 비교한다. 실제 Codex acceptance는 command trace와 Workspace evidence를 같은 개념으로 검증하되 transcript를 저장소에 남기지 않는다.
