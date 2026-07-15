#!/usr/bin/env python3
"""Run one connected product update, migration failure, success, and rollback journey."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path


from phase8_support import EvidenceLedger, capture, cli, request_file
from run_phase6_product_update import apply, package, synthetic_product
from run_phase7_migration import add_custom_migration
from run_phase7_planning import add_migration, release_tree


CONTEXT_MARKER = "PRODUCT_LIFECYCLE_CONTEXT"


def release_env(releases: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_DIR": str(releases)})
    return env


def add_existing_assets(base: Path, releases: Path, version: str) -> None:
    source = base / f"assets-product-{version}"
    target = releases / f"v{version}"
    if not source.is_dir():
        raise AssertionError(f"missing packaged assets: {source}")
    shutil.copytree(source, target)


def product_version(workspace: Path) -> tuple[str, str]:
    return (
        (workspace / ".podo/VERSION").read_text(encoding="utf-8").strip(),
        (workspace / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip(),
    )


def evidence(workspace: Path) -> dict[str, tuple[str, int]]:
    paths = [workspace / "user_config.md", workspace / "WORKSPACE_VERSION"]
    for root_name in ("events", "deltas", "state"):
        paths.extend(path for path in sorted((workspace / root_name).rglob("*")) if path.is_file())
    values: dict[str, tuple[str, int]] = {}
    for path in paths:
        relative = path.relative_to(workspace).as_posix()
        values[relative] = (
            hashlib.sha256(path.read_bytes()).hexdigest(),
            stat.S_IMODE(path.stat().st_mode),
        )
    return values


def create_context(workspace: Path, root: Path) -> Path:
    capture_id, _ = capture(workspace, root, "product-context")
    state_text = "\n".join(
        [
            "# Product Lifecycle",
            "",
            "Updated: 2026-07-15",
            "",
            "## Current Context",
            "",
            CONTEXT_MARKER,
            "",
            "## Current Decisions",
            "",
            "- 제품 변경 중에도 이 Context를 보존한다.",
            "",
            "## Reasons",
            "",
            "- [Relevant Delta]({{DELTA_LINK}})",
            "",
        ]
    )
    request = request_file(
        workspace,
        "product-context",
        {
            "event": {"title": "Product lifecycle Context", "context": "Phase 8 synthetic product journey."},
            "updates": [
                {
                    "state_slug": "project",
                    "expected_state_sha256": None,
                    "delta_title": "Product lifecycle Context",
                    "changed": f"- {CONTEXT_MARKER}",
                    "why": "제품 lifecycle 전체에서 사용자 Context 보존을 검증한다.",
                    "confidence": "confirmed",
                    "needs_confirmation": "- 없음",
                    "state_markdown": state_text,
                }
            ],
        },
    )
    applied = cli(
        workspace,
        "context",
        "apply",
        "--capture",
        capture_id,
        "--request",
        str(request),
    )
    if applied.returncode:
        raise AssertionError(applied.stdout + applied.stderr)
    state = workspace / "state/project.md"
    state.chmod(0o600)
    return state


def json_result(result) -> dict:
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def run_journey(run_id: str) -> dict:
    ledger = EvidenceLedger("product", run_id)
    with tempfile.TemporaryDirectory(prefix=f"podo-phase8-product-{run_id}-") as temporary:
        base = Path(temporary)
        old_product = synthetic_product(base, "0.8.0", [1])
        old_package, old_metadata = package(base, old_product, "1")
        compatible_product = synthetic_product(base, "0.9.0", [1])
        releases, _ = release_tree(base, compatible_product, "2")
        add_existing_assets(base, releases, "0.8.0")

        target_product = synthetic_product(base, "1.0.0", [2])
        add_migration(target_product, 1, 2)
        release_tree(base, target_product, "3")

        failing_product = synthetic_product(base, "1.0.1", [2])
        add_custom_migration(
            failing_product,
            "import argparse\np=argparse.ArgumentParser();p.add_argument('--workspace');p.parse_args()\nraise SystemExit(23)\n",
        )
        release_tree(base, failing_product, "4")
        (releases / "latest").write_text("1.0.0\n", encoding="utf-8")
        env = release_env(releases)

        workspace = base / "workspace"
        installed = apply(old_package, old_metadata, workspace)
        if installed.returncode:
            raise AssertionError(installed.stdout + installed.stderr)
        config = workspace / "user_config.md"
        config.write_text(
            """# User Configuration

- Assistant name: 제품포도
- Personality: 승인 경계를 분명히 설명함
- Response style: product와 Workspace version을 간결하게 답함

## Explicit Defaults

- 합성 Release만 사용한다.

## Allowed External Sources

- 현재 테스트가 지정한 local Release
""",
            encoding="utf-8",
        )
        config.chmod(0o640)
        state = create_context(workspace, base)
        original = evidence(workspace)
        if product_version(workspace) != ("0.8.0", "1"):
            raise AssertionError(str(product_version(workspace)))
        ledger.passed(
            "product-baseline",
            ("3", "5", "7"),
            "Workspace 1 contains traceable user Context",
            "product 0.8.0 baseline and user file modes pinned",
        )

        updated = cli(workspace, "update", "--version", "0.9.0", env=env)
        if updated.returncode or "UPDATED" not in updated.stdout:
            raise AssertionError(updated.stdout + updated.stderr)
        if product_version(workspace) != ("0.9.0", "1") or evidence(workspace) != original:
            raise AssertionError("compatible product update changed user evidence")
        rolled_back = cli(workspace, "update", "--version", "0.8.0", env=env)
        if rolled_back.returncode or "ROLLED_BACK" not in rolled_back.stdout:
            raise AssertionError(rolled_back.stdout + rolled_back.stderr)
        if product_version(workspace) != ("0.8.0", "1") or evidence(workspace) != original:
            raise AssertionError("exact-version product rollback changed user evidence")
        ledger.passed(
            "compatible-update-rollback",
            ("3", "10"),
            "compatible update reached product 0.9.0 only",
            "exact-version rollback restored product 0.8.0",
            "all user bytes and modes remained pinned",
        )

        plans = workspace / ".podo-work/migration-plans"
        before_reject = evidence(workspace)
        incompatible = cli(workspace, "update", "--version", "1.0.0", env=env)
        if incompatible.returncode == 0 or "E_WORKSPACE_INCOMPATIBLE" not in incompatible.stderr:
            raise AssertionError(incompatible.stdout + incompatible.stderr)
        if product_version(workspace) != ("0.8.0", "1") or evidence(workspace) != before_reject:
            raise AssertionError("incompatible update changed product or user evidence")
        if plans.exists() and list(plans.glob("*.json")):
            raise AssertionError("normal incompatible update created a migration plan")
        if list((workspace / ".podo-backups").glob("*")):
            raise AssertionError("normal incompatible update created a backup")
        ledger.passed(
            "incompatible-update-stop",
            ("10",),
            "normal update stopped on Workspace incompatibility",
            "no migration plan or backup was created",
        )

        failed_plan = json_result(
            cli(workspace, "migrate", "--version", "1.0.1", "--json", env=env)
        )
        before_failure = evidence(workspace)
        failed = cli(
            workspace,
            "migrate",
            "--apply",
            failed_plan["plan_id"],
            "--json",
            env=env,
        )
        if failed.returncode == 0 or "E_MIGRATION_ENTRYPOINT" not in failed.stderr:
            raise AssertionError(failed.stdout + failed.stderr)
        if product_version(workspace) != ("0.8.0", "1") or evidence(workspace) != before_failure:
            raise AssertionError("failed migration changed current product or user evidence")
        failed_backup = workspace / ".podo-backups" / failed_plan["backup_id"] / "backup.json"
        if not failed_backup.is_file():
            raise AssertionError("failed migration did not retain a complete backup")
        ledger.passed(
            "migration-failure-restore",
            ("10", "11"),
            "exact migration plan created before apply",
            "failing staged entrypoint restored product and user evidence",
            "complete pre-migration backup retained",
        )

        migration_plan = json_result(
            cli(workspace, "migrate", "--version", "1.0.0", "--json", env=env)
        )
        if evidence(workspace) != original:
            raise AssertionError("successful migration planning changed user evidence")
        migrated = json_result(
            cli(
                workspace,
                "migrate",
                "--apply",
                migration_plan["plan_id"],
                "--json",
                env=env,
            )
        )
        if migrated.get("outcome") != "committed" or product_version(workspace) != ("1.0.0", "2"):
            raise AssertionError(str(migrated))
        if "Format: 2" not in state.read_text(encoding="utf-8") or CONTEXT_MARKER not in state.read_text(encoding="utf-8"):
            raise AssertionError(state.read_text(encoding="utf-8"))
        ledger.passed(
            "migration-success",
            ("10",),
            "separate exact plan migrated product 1.0.0 and Workspace 2 together",
            "existing Context marker survived the format change",
        )

        rollback_plan = json_result(
            cli(
                workspace,
                "migrate",
                "rollback",
                "--backup",
                migration_plan["backup_id"],
                "--json",
                env=env,
            )
        )
        if product_version(workspace) != ("1.0.0", "2"):
            raise AssertionError("rollback planning changed installed versions")
        restored = json_result(
            cli(
                workspace,
                "migrate",
                "--apply",
                rollback_plan["plan_id"],
                "--json",
                env=env,
            )
        )
        if restored.get("outcome") != "rollback-committed":
            raise AssertionError(str(restored))
        if product_version(workspace) != ("0.8.0", "1") or evidence(workspace) != original:
            raise AssertionError("full rollback did not restore the original product and user evidence")
        backups = sorted((workspace / ".podo-backups").glob("*/backup.json"))
        if len(backups) < 3:
            raise AssertionError(f"expected failure, migration and safety backups: {backups}")
        for backup in backups:
            value = json.loads(backup.read_text(encoding="utf-8"))
            if value.get("state") != "complete":
                raise AssertionError(str(value))
        ledger.passed(
            "full-rollback",
            ("10", "11"),
            "rollback review was non-applying",
            "exact full rollback restored product 0.8.0 and Workspace 1",
            f"{len(backups)} complete source and safety backups retained",
        )

        validated = cli(workspace, "validate")
        doctor = cli(workspace, "doctor", "--json")
        if validated.returncode or doctor.returncode:
            raise AssertionError(validated.stdout + validated.stderr + doctor.stdout + doctor.stderr)
        doctor_value = json.loads(doctor.stdout)
        if doctor_value.get("status") != "healthy" or CONTEXT_MARKER not in state.read_text(encoding="utf-8"):
            raise AssertionError(doctor.stdout + state.read_text(encoding="utf-8"))
        ledger.passed(
            "product-final",
            ("3", "10", "11"),
            "final Workspace validates and doctor is healthy",
            "original Context and file modes match the baseline",
        )
    ledger.emit()
    return ledger.value()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="standalone")
    args = parser.parse_args()
    run_journey(args.run_id)


if __name__ == "__main__":
    main()
