#!/usr/bin/env python3
"""Read-only diagnostics and approved recovery planning for Podo."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from transaction_store import (
    TransactionError,
    TransactionManager,
    atomic_json,
    strict_three_way_merge,
    tree_hash,
)


FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PLAIN_REFERENCE_RE = re.compile(
    r"(?<!\()(?P<path>(?:\.\.?/)+(?:events|deltas|state|people|research)/[A-Za-z0-9_./-]+(?:\.md|\.pdf))"
)
PLAN_ID_RE = re.compile(r"^recovery-[a-f0-9]{20}$")


class RecoveryError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json_safe(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, str(error)
    if not isinstance(value, dict):
        return None, "JSON root is not an object"
    return value, None


class RecoveryStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.work = self.root / ".podo-work"
        self.transactions = TransactionManager(self.root)
        self.recovery_plans = self.work / "recovery-plans"

    def finding(
        self,
        code: str,
        severity: str,
        summary: str,
        paths: list[str] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "summary": summary,
            "paths": paths or [],
            **extra,
        }

    def transaction_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        try:
            values = self.transactions.unfinished()
        except TransactionError as error:
            return [self.finding("PODO_D002_TRANSACTION_STORE_INVALID", "error", error.detail, [".podo-work/transactions"])]
        for transaction_id in values:
            path = f".podo-work/transactions/{transaction_id}"
            try:
                _, plan, journal = self.transactions.load(transaction_id)
            except TransactionError as error:
                findings.append(self.finding("PODO_D002_TRANSACTION_INVALID", "error", error.detail, [path], transaction_id=transaction_id))
                continue
            findings.append(
                self.finding(
                    "PODO_D001_TRANSACTION_INCOMPLETE",
                    "error",
                    f"Context transaction is {journal.get('state', 'unknown')} and was not auto-applied or deleted.",
                    [path],
                    transaction_id=transaction_id,
                    operation=plan.get("operation"),
                    state=journal.get("state"),
                    current_step=journal.get("current_step"),
                    completed=journal.get("completed", []),
                    failure=journal.get("failure"),
                    recovery="plan-available",
                )
            )
        return findings

    def unfinished_product_updates(self) -> list[str]:
        directory = self.work / "product-updates"
        if not directory.exists():
            return []
        if directory.is_symlink() or not directory.is_dir():
            return ["invalid-product-update-store"]
        return sorted(path.name for path in directory.iterdir() if path.is_dir() and not path.name.startswith("."))

    def product_update_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for update_id in self.unfinished_product_updates():
            if update_id == "invalid-product-update-store":
                findings.append(
                    self.finding(
                        "PODO_D311_PRODUCT_UPDATE_STORE_INVALID",
                        "error",
                        "Product update transaction store is not a regular directory.",
                        [".podo-work/product-updates"],
                    )
                )
                continue
            relative = f".podo-work/product-updates/{update_id}"
            journal, error = load_json_safe(self.root / relative / "journal.json")
            if error or journal is None:
                findings.append(
                    self.finding(
                        "PODO_D311_PRODUCT_UPDATE_INVALID",
                        "error",
                        error or "product update journal is invalid",
                        [relative],
                        update_id=update_id,
                    )
                )
                continue
            findings.append(
                self.finding(
                    "PODO_D310_PRODUCT_UPDATE_INCOMPLETE",
                    "error",
                    "Product update was interrupted and requires product recovery before another update.",
                    [relative],
                    update_id=update_id,
                    state=journal.get("state"),
                    from_version=journal.get("from_version"),
                    to_version=journal.get("to_version"),
                )
            )
        return findings

    def unfinished_migrations(self) -> list[str]:
        directory = self.work / "migrations"
        if not directory.exists():
            return []
        if directory.is_symlink() or not directory.is_dir():
            return ["invalid-migration-store"]
        return sorted(path.name for path in directory.iterdir() if path.is_dir() and not path.name.startswith("."))

    def migration_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for plan_id in self.unfinished_migrations():
            if plan_id == "invalid-migration-store":
                findings.append(
                    self.finding(
                        "PODO_D321_MIGRATION_STORE_INVALID",
                        "error",
                        "Workspace migration transaction store is not a regular directory.",
                        [".podo-work/migrations"],
                    )
                )
                continue
            relative = f".podo-work/migrations/{plan_id}"
            journal, error = load_json_safe(self.root / relative / "journal.json")
            if error or journal is None:
                findings.append(
                    self.finding(
                        "PODO_D321_MIGRATION_INVALID",
                        "error",
                        error or "migration journal is invalid",
                        [relative],
                        plan_id=plan_id,
                    )
                )
                continue
            findings.append(
                self.finding(
                    "PODO_D320_MIGRATION_INCOMPLETE",
                    "error",
                    "Workspace migration or full rollback was interrupted; do not update, migrate, or delete its backup.",
                    [relative, f".podo-backups/{journal.get('backup_id') or journal.get('safety_backup_id', 'unknown')}"],
                    plan_id=plan_id,
                    state=journal.get("state"),
                    backup_id=journal.get("backup_id"),
                    source_backup_id=journal.get("source_backup_id"),
                    safety_backup_id=journal.get("safety_backup_id"),
                )
            )
        return findings

    def workspace_findings(self) -> list[dict[str, Any]]:
        validator = self.root / ".podo/scripts/validate_workspace.py"
        result = subprocess.run(
            [sys.executable, str(validator), str(self.root), "--mode", "context-present"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode == 0:
            return []
        findings: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            code, _, detail = line.partition(" ")
            path_value = detail.split(":", 1)[0] if ":" in detail else ""
            findings.append(
                self.finding(
                    f"PODO_D100_{code}",
                    "error",
                    detail or code,
                    [path_value] if path_value else [],
                    validator_code=code,
                )
            )
        return findings

    def related_original_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for metadata in sorted((self.root / "events").glob("*/*/*/metadata.md")):
            text = metadata.read_text(encoding="utf-8")
            fields = {match.group(1): match.group(2).strip() for match in FIELD_RE.finditer(text)}
            related_value = fields.get("Related-Original")
            if not related_value:
                continue
            related = (metadata.parent / related_value).resolve()
            relative = metadata.relative_to(self.root).as_posix()
            try:
                related.relative_to((metadata.parent / "original").resolve())
            except ValueError:
                findings.append(self.finding("PODO_D110_RELATED_ORIGINAL_INVALID", "error", "Related original escapes Event original directory.", [relative]))
                continue
            if not related.is_file() or related.is_symlink():
                findings.append(self.finding("PODO_D111_RELATED_ORIGINAL_MISSING", "error", "Related deferred original is missing.", [relative, related.relative_to(self.root).as_posix()]))
                continue
            if fields.get("Related-SHA-256") != sha256_file(related):
                findings.append(self.finding("PODO_D112_RELATED_ORIGINAL_HASH", "error", "Related deferred original hash does not match Metadata.", [relative]))
        return findings

    def context_lifecycle_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        inbox = self.work / "inbox"
        deferred = self.work / "deferred"
        receipts = self.work / "receipts"
        for path in sorted(deferred.glob("*.json")) if deferred.is_dir() else []:
            capture_id = path.stem
            capture = inbox / capture_id
            if not capture.is_dir():
                findings.append(self.finding("PODO_D201_DEFERRED_WITHOUT_CAPTURE", "error", "Deferred decision has no source capture.", [path.relative_to(self.root).as_posix()]))
        for path in sorted(receipts.glob("*.json")) if receipts.is_dir() else []:
            value, error = load_json_safe(path)
            relative = path.relative_to(self.root).as_posix()
            if error or value is None:
                findings.append(self.finding("PODO_D202_RECEIPT_INVALID", "error", error or "invalid receipt", [relative]))
                continue
            capture_id = str(value.get("capture_id") or path.stem)
            capture = inbox / capture_id
            transaction_id = value.get("transaction_id")
            transaction_pending = isinstance(transaction_id, str) and (self.work / f"transactions/{transaction_id}").is_dir()
            if capture.is_dir() and not transaction_pending:
                findings.append(self.finding("PODO_D203_PROCESSED_CAPTURE_REMAINS", "warning", "Processed capture remains after its final receipt.", [capture.relative_to(self.root).as_posix(), relative]))
            if value.get("outcome") == "applied":
                for field in ("event", "deltas", "states", "people", "research"):
                    items = value.get(field, [])
                    if isinstance(items, str):
                        items = [items]
                    if not isinstance(items, list):
                        findings.append(self.finding("PODO_D204_RECEIPT_TARGET_INVALID", "error", f"Receipt {field} is not a path list.", [relative]))
                        continue
                    for target_value in items:
                        target = self.root / str(target_value)
                        if not target.exists():
                            findings.append(self.finding("PODO_D205_RECEIPT_TARGET_MISSING", "error", f"Applied receipt target is missing: {target_value}", [relative, str(target_value)]))
        return findings

    def product_findings(self) -> list[dict[str, Any]]:
        manifest_path = self.root / ".podo/install-manifest.json"
        if not manifest_path.is_file():
            return [self.finding("PODO_D301_PRODUCT_MANIFEST_MISSING", "warning", "Local install manifest is unavailable; product modification cannot be verified.", [".podo/install-manifest.json"])]
        manifest, error = load_json_safe(manifest_path)
        if error or manifest is None:
            return [self.finding("PODO_D302_PRODUCT_MANIFEST_INVALID", "error", error or "invalid manifest", [".podo/install-manifest.json"])]
        expected = manifest.get("product_files")
        if not isinstance(expected, dict):
            return [self.finding("PODO_D302_PRODUCT_MANIFEST_INVALID", "error", "product_files is missing", [".podo/install-manifest.json"])]
        actual: dict[str, dict[str, str]] = {}
        candidates = [self.root / "AGENTS.md"]
        for directory in (self.root / ".codex", self.root / ".podo"):
            if directory.is_dir():
                candidates.extend(sorted(directory.rglob("*")))
        for path in candidates:
            relative = path.relative_to(self.root).as_posix()
            if relative == ".podo/install-manifest.json" or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            if path.is_file() and not path.is_symlink():
                actual[relative] = {"sha256": sha256_file(path), "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
        if dict(sorted(actual.items())) == expected:
            return []
        changed = sorted(set(actual) ^ set(expected))
        if not changed:
            changed = sorted(path for path in actual if actual[path] != expected.get(path))
        return [self.finding("PODO_D303_PRODUCT_MODIFIED", "error", "Installed product files differ from the verified manifest.", changed[:20])]

    def hook_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        hook = self.root / ".codex/hooks.json"
        try:
            value = json.loads(hook.read_text(encoding="utf-8"))
            command = value["hooks"]["Stop"][0]["hooks"][0]["command"]
        except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError):
            command = None
        if command != "./.podo/scripts/capture_event":
            findings.append(self.finding("PODO_D401_HOOK_INVALID", "error", "Stop hook is missing or differs from the installed definition.", [".codex/hooks.json"]))
        health_path = self.work / "capture-health.json"
        health, error = load_json_safe(health_path) if health_path.is_file() else (None, None)
        if health is None:
            findings.append(self.finding("PODO_D402_CAPTURE_NOT_DIAGNOSED", "warning", "Capture entrypoint has no successful local diagnosis yet.", [".podo-work/capture-health.json"]))
        elif error or health.get("status") != "ready":
            findings.append(self.finding("PODO_D403_CAPTURE_UNHEALTHY", "error", error or str(health.get("code") or "capture health is not ready"), [".podo-work/capture-health.json"]))
        return findings

    def duplicate_context_findings(self) -> list[dict[str, Any]]:
        from knowledge_views import KnowledgeViews

        findings: list[dict[str, Any]] = []
        for duplicate in KnowledgeViews(self.root).duplicate_lines():
            paths = [f"{value['path']}:{value['line']}" for value in duplicate["locations"]]
            findings.append(
                self.finding(
                    "PODO_D120_CONTEXT_DUPLICATE",
                    "warning",
                    f"Exact current Context appears in multiple documents: {duplicate['text'][:120]}",
                    paths,
                )
            )
        return findings

    def plain_reference_findings(self) -> list[dict[str, Any]]:
        paths = list((self.root / "state").glob("*.md"))
        paths.extend((self.root / "people").glob("*.md"))
        paths.extend((self.root / "research/topics").glob("*.md"))
        paths.extend((self.root / "research/projects").glob("*.md"))
        paths.extend((self.root / "research/papers").glob("*/notes.md"))
        findings: list[dict[str, Any]] = []
        for path in sorted(value for value in paths if value.is_file() and not value.is_symlink()):
            text = path.read_text(encoding="utf-8")
            spans = [match.span() for match in LINK_RE.finditer(text)]
            for match in PLAIN_REFERENCE_RE.finditer(text):
                if any(start <= match.start() and match.end() <= end for start, end in spans):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                relative = path.relative_to(self.root).as_posix()
                findings.append(
                    self.finding(
                        "PODO_D121_PLAIN_REFERENCE",
                        "warning",
                        f"Legacy tracking path should become a Markdown link: {match.group('path')}",
                        [f"{relative}:{line}"],
                    )
                )
        return findings

    def doctor(self) -> dict[str, Any]:
        findings = (
            self.transaction_findings()
            + self.product_update_findings()
            + self.migration_findings()
            + self.workspace_findings()
            + self.related_original_findings()
            + self.context_lifecycle_findings()
            + self.product_findings()
            + self.hook_findings()
            + self.duplicate_context_findings()
            + self.plain_reference_findings()
        )
        findings.sort(key=lambda item: (item["severity"], item["code"], item["paths"]))
        status = "healthy"
        if any(item["severity"] == "error" for item in findings):
            status = "error"
        elif findings:
            status = "warning"
        return {
            "doctor_version": 1,
            "status": status,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "finding_count": len(findings),
            "findings": findings,
        }

    def fingerprint(self, path: Path) -> dict[str, Any]:
        if path.is_symlink():
            return {"kind": "symlink", "target": os.readlink(path)}
        if not path.exists():
            return {"kind": "missing"}
        if path.is_file():
            return {
                "kind": "file",
                "sha256": sha256_file(path),
                "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
            }
        if path.is_dir():
            return {
                "kind": "directory",
                "tree_sha256": tree_hash(path),
                "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
            }
        return {"kind": "other"}

    def add_pin(self, pins: dict[str, dict[str, Any]], path: Path) -> None:
        relative = self.transactions.relative(path)
        pins[relative] = self.fingerprint(path)

    def exact_file_or_missing(
        self,
        entry: dict[str, Any],
        manual: list[str],
    ) -> None:
        target = self.transactions.rooted(str(entry["target"]))
        current = self.fingerprint(target)
        if current["kind"] == "missing":
            return
        if current["kind"] == "file" and current.get("sha256") == entry["sha256"]:
            return
        manual.append(f"{entry['target']} is neither absent nor the staged file")

    def analyze_state(
        self,
        directory: Path,
        entry: dict[str, Any],
        manual: list[str],
    ) -> None:
        target = self.transactions.rooted(str(entry["target"]))
        current = self.fingerprint(target)
        if current["kind"] == "file" and current.get("sha256") == entry["new_sha256"]:
            return
        expected = entry.get("expected_sha256")
        if current["kind"] == "missing" and expected is None:
            return
        if current["kind"] == "file" and current.get("sha256") == expected:
            return
        original_value = entry.get("original")
        if current["kind"] != "file" or not original_value:
            manual.append(f"{entry['target']} was created, removed or changed type outside the transaction")
            return
        original = directory / str(original_value)
        staged = directory / str(entry["staged"])
        try:
            merged = strict_three_way_merge(
                original.read_text(encoding="utf-8"),
                target.read_text(encoding="utf-8"),
                staged.read_text(encoding="utf-8"),
            )
        except (OSError, UnicodeError) as error:
            manual.append(f"{entry['target']} cannot be compared safely: {error}")
            return
        if merged is None:
            manual.append(f"{entry['target']} has overlapping concurrent changes")

    def build_transaction_recovery(self, transaction_id: str) -> dict[str, Any]:
        directory, transaction_plan, journal = self.transactions.load(transaction_id)
        manual: list[str] = []
        event = transaction_plan["event"]
        event_target = self.transactions.rooted(str(event["target"]))
        event_current = self.fingerprint(event_target)
        if event_current["kind"] != "missing" and not (
            event_current["kind"] == "directory"
            and event_current.get("tree_sha256") == event["tree_sha256"]
        ):
            manual.append(f"{event['target']} is neither absent nor the staged Event")
        for entry in transaction_plan["deltas"] + transaction_plan["receipts"]:
            self.exact_file_or_missing(entry, manual)
        for entry in transaction_plan["states"]:
            self.analyze_state(directory, entry, manual)

        pins: dict[str, dict[str, Any]] = {}
        for relative in ("plan.json", "journal.json", "staged", "originals"):
            self.add_pin(pins, directory / relative)
        targets = [event["target"]]
        targets.extend(entry["target"] for key in ("deltas", "states", "receipts") for entry in transaction_plan[key])
        cleanup = [entry["path"] for entry in transaction_plan.get("cleanup", [])]
        for value in targets + cleanup:
            self.add_pin(pins, self.transactions.rooted(str(value)))

        action = "manual-confirmation-required" if manual else "resume-transaction"
        material = {
            "transaction_id": transaction_id,
            "action": action,
            "pins": pins,
            "manual_reasons": manual,
        }
        digest = hashlib.sha256(
            json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:20]
        plan_id = f"recovery-{digest}"
        return {
            "recovery_plan_version": 1,
            "plan_id": plan_id,
            "status": "planned",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id,
            "transaction_state": journal.get("state"),
            "action": action,
            "impact": {
                "targets": targets,
                "cleanup_after_validation": cleanup,
                "preserves_transaction_until_success": True,
            },
            "manual_reasons": manual,
            "pins": dict(sorted(pins.items())),
        }

    def save_recovery_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        path = self.recovery_plans / f"{plan['plan_id']}.json"
        if path.is_symlink():
            raise RecoveryError("E_RECOVERY_PLAN_PATH", str(path.relative_to(self.root)))
        if path.is_file():
            existing, error = load_json_safe(path)
            if error or existing is None:
                raise RecoveryError("E_RECOVERY_PLAN_INVALID", error or plan["plan_id"])
            return existing
        atomic_json(path, plan)
        return plan

    def plan_recovery(self) -> dict[str, Any]:
        plans: list[dict[str, Any]] = []
        manual: list[dict[str, str]] = []
        try:
            transaction_ids = self.transactions.unfinished()
        except TransactionError as error:
            raise RecoveryError(error.code, error.detail) from error
        for transaction_id in transaction_ids:
            try:
                plan = self.save_recovery_plan(self.build_transaction_recovery(transaction_id))
            except TransactionError as error:
                manual.append({"transaction_id": transaction_id, "code": error.code, "detail": error.detail})
                continue
            plans.append(
                {
                    "plan_id": plan["plan_id"],
                    "transaction_id": transaction_id,
                    "action": plan["action"],
                    "impact": plan["impact"],
                    "manual_reasons": plan["manual_reasons"],
                }
            )
        if not plans and not manual:
            return {"recovery_version": 1, "status": "nothing-to-recover", "plans": [], "manual": []}
        status = "manual-required" if manual or any(plan["action"] != "resume-transaction" for plan in plans) else "planned"
        return {"recovery_version": 1, "status": status, "plans": plans, "manual": manual}

    def load_recovery_plan(self, plan_id: str) -> tuple[Path, dict[str, Any]]:
        if not PLAN_ID_RE.fullmatch(plan_id):
            raise RecoveryError("E_RECOVERY_PLAN_ID", plan_id)
        path = self.recovery_plans / f"{plan_id}.json"
        if path.is_symlink() or not path.is_file():
            raise RecoveryError("E_RECOVERY_PLAN_MISSING", plan_id)
        value, error = load_json_safe(path)
        if error or value is None or value.get("plan_id") != plan_id:
            raise RecoveryError("E_RECOVERY_PLAN_INVALID", error or "plan identity mismatch")
        return path, value

    def verify_pins(self, pins: Any) -> None:
        if not isinstance(pins, dict) or not pins:
            raise RecoveryError("E_RECOVERY_PLAN_INVALID", "pins are missing")
        for relative, expected in sorted(pins.items()):
            if not isinstance(relative, str) or not isinstance(expected, dict):
                raise RecoveryError("E_RECOVERY_PLAN_INVALID", "pin is invalid")
            try:
                actual = self.fingerprint(self.transactions.rooted(relative))
            except TransactionError as error:
                raise RecoveryError(error.code, error.detail) from error
            if actual != expected:
                raise RecoveryError("E_RECOVERY_PLAN_STALE", relative)

    def apply_recovery(self, plan_id: str) -> dict[str, Any]:
        path, plan = self.load_recovery_plan(plan_id)
        if plan.get("status") == "applied":
            return {
                "status": "already-applied",
                "plan_id": plan_id,
                "transaction_id": plan.get("transaction_id"),
                "result": plan.get("result"),
            }
        if plan.get("status") != "planned" or plan.get("action") != "resume-transaction":
            raise RecoveryError("E_RECOVERY_MANUAL_REQUIRED", plan_id)
        self.verify_pins(plan.get("pins"))
        from context_store import ContextStore

        store = ContextStore(self.root)
        try:
            result = self.transactions.commit(
                str(plan["transaction_id"]),
                store.validate_workspace,
                lambda text, slug: store.validate_current_text(text, slug, requires_delta_token=False),
            )
        except TransactionError as error:
            raise RecoveryError(error.code, error.detail) from error
        plan["status"] = "applied"
        plan["applied_at"] = datetime.now(timezone.utc).isoformat()
        plan["result"] = result
        atomic_json(path, plan)
        return {
            "status": "applied",
            "plan_id": plan_id,
            "transaction_id": plan["transaction_id"],
            "result": result,
        }
