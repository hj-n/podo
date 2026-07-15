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

from transaction_store import TransactionError, TransactionManager


FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$", re.MULTILINE)


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
                for field in ("event", "deltas", "states"):
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

    def doctor(self) -> dict[str, Any]:
        findings = (
            self.transaction_findings()
            + self.workspace_findings()
            + self.related_original_findings()
            + self.context_lifecycle_findings()
            + self.product_findings()
            + self.hook_findings()
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
