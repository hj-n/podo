# Workspace Migrations

이 디렉터리는 verified target product가 제공하는 사용자 데이터 migration을 보관한다. 현재 Podo 0.6.0 candidate는 Workspace 1과 호환되며 실제 migration을 포함하지 않는다.

실제 형식 변경이 필요한 product는 다음 구조를 사용한다.

```text
.podo/migrations/
└── 1-to-2/
    ├── migration.json
    └── migrate.py
```

`migration.json` 예시:

```json
{
  "migration_contract_version": 1,
  "from_workspace_version": 1,
  "to_workspace_version": 2,
  "description": "State 문서에 새 format marker를 추가한다.",
  "changes": ["State header에 Format 필드를 추가한다."],
  "affected_paths": ["state/project.md"],
  "entrypoint": "migrate.py"
}
```

- 시작과 목표 version은 directory 이름과 일치해야 한다.
- 영향 path는 `user_config.md`, `events/`, `deltas/`, `state/` 아래의 exact relative path만 허용한다.
- `WORKSPACE_VERSION`은 engine이 마지막에 변경하므로 descriptor에 쓰지 않는다.
- Entrypoint는 `python3 migrate.py --workspace <staged-workspace>`로 실행되고 staged Workspace 밖을 migration 대상으로 사용하지 않는다.
- 선언하지 않은 사용자 path가 달라지면 apply 전에 중단한다.
- 실제 Workspace에서 직접 실행하지 않고 `podo migrate`의 plan, backup과 transaction을 통해서만 실행한다.
