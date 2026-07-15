#!/usr/bin/env python3
"""Validate a Podo User Workspace using the checked-in Phase 1 contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
EVENT_PATH_RE = re.compile(r"^events/(\d{4})/(\d{2})/\d{4}-\d{2}-\d{2}_\d{6}-[a-z0-9][a-z0-9-]*/metadata\.md$")
DELTA_PATH_RE = re.compile(r"^deltas/(\d{4})/(\d{2})/\d{4}-\d{2}-\d{2}_\d{6}-[a-z0-9][a-z0-9-]*\.md$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
TODO_RE = re.compile(r"^- \[([ xX])\]\s+(.+)$")
TODO_FIELD_RE = re.compile(r"^\s+- (Created|Due|Completed|Result):\s*(.+)$")
TOKEN_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")


@dataclass(order=True)
class Problem:
    code: str
    path: str
    message: str


class Validator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.problems: list[Problem] = []
        self.contracts = self.root / ".podo/contracts"

    def add(self, code: str, path: Path | str, message: str) -> None:
        if isinstance(path, Path):
            try:
                display = path.resolve().relative_to(self.root).as_posix()
            except ValueError:
                display = str(path)
        else:
            display = path
        self.problems.append(Problem(code, display, message))

    def load_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            self.add("E_CONTRACT", path, f"cannot read JSON contract: {error}")
            return {}

    def fields(self, text: str) -> dict[str, str]:
        return {match.group(1): match.group(2).strip() for match in FIELD_RE.finditer(text)}

    def safe_target(self, source: Path, value: str, code: str) -> Path | None:
        if "://" in value or value.startswith("/"):
            self.add(code, source, f"link must be relative: {value}")
            return None
        target = (source.parent / value).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            self.add(code, source, f"link escapes Workspace: {value}")
            return None
        if not target.exists():
            self.add(code, source, f"link target does not exist: {value}")
            return None
        return target

    def validate_required_paths(self) -> None:
        required_files = (
            "AGENTS.md",
            ".codex/hooks.json",
            ".podo/VERSION",
            ".podo/contracts/ownership.json",
            ".podo/contracts/hook_stop.json",
            ".podo/contracts/transcript_adapter.json",
            ".podo/contracts/versions.json",
            ".podo/contracts/context_files.json",
            "WORKSPACE_VERSION",
            "user_config.md",
        )
        required_dirs = (
            ".podo-work",
            ".podo-backups",
            "events",
            "deltas",
            "state",
        )
        for relative in required_files:
            path = self.root / relative
            if not path.is_file():
                self.add("E_REQUIRED_PATH", relative, "required file is missing")
        for relative in required_dirs:
            path = self.root / relative
            if not path.is_dir():
                self.add("E_REQUIRED_PATH", relative, "required directory is missing")

    def validate_versions(self) -> None:
        contract = self.load_json(self.contracts / "versions.json")
        try:
            product_version = (self.root / ".podo/VERSION").read_text(encoding="utf-8").strip()
            workspace_raw = (self.root / "WORKSPACE_VERSION").read_text(encoding="utf-8").strip()
        except OSError:
            return
        if not SEMVER_RE.fullmatch(product_version):
            self.add("E_VERSION", ".podo/VERSION", "product version must be MAJOR.MINOR.PATCH")
        try:
            workspace_version = int(workspace_raw)
            if workspace_version < 1:
                raise ValueError
        except ValueError:
            self.add("E_VERSION", "WORKSPACE_VERSION", "Workspace version must be a positive integer")
            return
        compatible = contract.get("compatible", {}).get(product_version, [])
        if workspace_version not in compatible:
            self.add(
                "E_VERSION_COMPATIBILITY",
                "WORKSPACE_VERSION",
                f"product {product_version} does not declare Workspace {workspace_version} compatible",
            )

    def validate_ownership(self) -> None:
        contract = self.load_json(self.contracts / "ownership.json")
        product = set(contract.get("product_owned", []))
        user = set(contract.get("user_owned", []))
        overlap = sorted(product & user)
        for value in overlap:
            self.add("E_OWNERSHIP", ".podo/contracts/ownership.json", f"path appears in both ownership sets: {value}")
        required_product = {"AGENTS.md", ".codex/hooks.json", ".podo/**"}
        if not required_product.issubset(product):
            self.add("E_OWNERSHIP", ".podo/contracts/ownership.json", "canonical product-owned paths are incomplete")

    def validate_hook(self) -> None:
        hook_path = self.root / ".codex/hooks.json"
        hook_contract = self.load_json(self.contracts / "hook_stop.json")
        hook = self.load_json(hook_path)
        try:
            handlers = hook["hooks"]["Stop"]
            command_handler = handlers[0]["hooks"][0]
        except (KeyError, IndexError, TypeError):
            self.add("E_HOOK", hook_path, "Stop command hook is missing")
            return
        if command_handler.get("type") != "command":
            self.add("E_HOOK", hook_path, "Stop hook type must be command")
        expected = "./" + hook_contract.get("entrypoint", "")
        if command_handler.get("command") != expected:
            self.add("E_HOOK", hook_path, f"command must be {expected}")
        entrypoint = self.root / hook_contract.get("entrypoint", "")
        if not entrypoint.is_file() or not os.access(entrypoint, os.X_OK):
            self.add("E_HOOK", hook_path, "capture entrypoint must exist and be executable")
        timeout = command_handler.get("timeout")
        if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
            self.add("E_HOOK", hook_path, "timeout must be an integer from 1 to 60 seconds")
        command = str(command_handler.get("command", ""))
        if re.search(r"https?://|curl\b|wget\b|nc\b", command):
            self.add("E_HOOK", hook_path, "hook command must not send data externally")

    def validate_user_config(self) -> None:
        path = self.root / "user_config.md"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return
        for label in ("Assistant name", "Personality"):
            match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", text, re.MULTILINE)
            if not match or not match.group(1).strip() or TOKEN_RE.search(match.group(1)):
                self.add("E_USER_CONFIG", path, f"{label} must contain an explicit value")

    def validate_events(self, context_contract: dict) -> None:
        allowed = set(context_contract.get("event", {}).get("completeness_values", []))
        required = context_contract.get("event", {}).get("required_metadata_fields", [])
        for metadata in sorted((self.root / "events").glob("*/*/*/metadata.md")):
            relative = metadata.relative_to(self.root).as_posix()
            match = EVENT_PATH_RE.fullmatch(relative)
            if not match:
                self.add("E_EVENT_PATH", metadata, "Event metadata path does not follow the contract")
            else:
                if match.group(2) not in {f"{month:02d}" for month in range(1, 13)}:
                    self.add("E_EVENT_PATH", metadata, "Event month must be 01 through 12")
            text = metadata.read_text(encoding="utf-8")
            fields = self.fields(text)
            for field in required:
                if not fields.get(field):
                    self.add("E_EVENT_FIELD", metadata, f"required field is missing: {field}")
            for field in ("Occurred", "Captured"):
                value = fields.get(field)
                if value:
                    try:
                        datetime.fromisoformat(value.replace("Z", "+00:00"))
                        if "T" not in value or not re.search(r"(Z|[+-]\d{2}:\d{2})$", value):
                            raise ValueError
                    except ValueError:
                        self.add("E_EVENT_TIMESTAMP", metadata, f"{field} must be RFC3339 with timezone")
            completeness = fields.get("Completeness")
            if completeness and completeness not in allowed:
                self.add("E_EVENT_COMPLETENESS", metadata, f"unknown completeness: {completeness}")
            missing = fields.get("Missing-Record-Families", "")
            if completeness == "complete-local-transcript" and missing != "none":
                self.add("E_EVENT_COMPLETENESS", metadata, "complete original must declare no missing record families")
            if completeness == "partial" and missing in {"", "none"}:
                self.add("E_EVENT_COMPLETENESS", metadata, "partial original must name missing record families")
            original_value = fields.get("Original-Entrypoint")
            if not original_value:
                continue
            original = self.safe_target(metadata, original_value, "E_EVENT_ORIGINAL")
            if original is None or not original.is_file():
                continue
            digest = hashlib.sha256(original.read_bytes()).hexdigest()
            if fields.get("SHA-256") != digest:
                self.add("E_EVENT_HASH", metadata, "SHA-256 does not match original bytes")
            original_dir = (metadata.parent / "original").resolve()
            try:
                original.relative_to(original_dir)
            except ValueError:
                self.add("E_EVENT_ORIGINAL", metadata, "original entrypoint must stay inside Event original/")
        if not list((self.root / "events").glob("*/*/*/metadata.md")):
            self.add("E_EVENT_MISSING", "events", "at least one synthetic Event is required")

    def validate_deltas(self, context_contract: dict) -> None:
        required = context_contract.get("delta", {}).get("required_fields", [])
        confidence_values = set(context_contract.get("delta", {}).get("confidence_values", []))
        found = False
        for path in sorted((self.root / "deltas").glob("*/*/*.md")):
            found = True
            relative = path.relative_to(self.root).as_posix()
            if not DELTA_PATH_RE.fullmatch(relative):
                self.add("E_DELTA_PATH", path, "Delta path does not follow the contract")
            text = path.read_text(encoding="utf-8")
            fields = self.fields(text)
            for field in required:
                if not fields.get(field):
                    self.add("E_DELTA_FIELD", path, f"required field is missing: {field}")
            confidence = fields.get("Confidence")
            if confidence and confidence not in confidence_values:
                self.add("E_DELTA_FIELD", path, f"unknown Confidence: {confidence}")
            occurred = fields.get("Occurred")
            if occurred:
                try:
                    datetime.fromisoformat(occurred.replace("Z", "+00:00"))
                except ValueError:
                    self.add("E_DELTA_FIELD", path, "Occurred must be RFC3339")
            for field, expected_suffix in (("Based-On", "metadata.md"), ("Affects", ".md")):
                value = fields.get(field, "")
                link = LINK_RE.search(value)
                if not link:
                    self.add("E_DELTA_LINK", path, f"{field} must be a Markdown link")
                    continue
                target = self.safe_target(path, link.group(1), "E_DELTA_LINK")
                if target and not target.as_posix().endswith(expected_suffix):
                    self.add("E_DELTA_LINK", path, f"{field} points to the wrong file type")
        if not found:
            self.add("E_DELTA_MISSING", "deltas", "at least one synthetic Delta is required")

    def validate_states(self) -> None:
        found = False
        for path in sorted((self.root / "state").glob("*.md")):
            found = True
            text = path.read_text(encoding="utf-8")
            fields = self.fields(text)
            updated = fields.get("Updated")
            if not updated:
                self.add("E_STATE_FIELD", path, "Updated is required")
            else:
                try:
                    date.fromisoformat(updated)
                except ValueError:
                    self.add("E_STATE_FIELD", path, "Updated must be YYYY-MM-DD")
            lines = text.splitlines()
            for index, line in enumerate(lines):
                todo = TODO_RE.match(line)
                if not todo:
                    continue
                checked = todo.group(1).lower() == "x"
                todo_fields: dict[str, str] = {}
                for following in lines[index + 1 :]:
                    if TODO_RE.match(following) or following.startswith("## "):
                        break
                    field = TODO_FIELD_RE.match(following)
                    if field:
                        todo_fields[field.group(1)] = field.group(2).strip()
                if "Created" not in todo_fields:
                    self.add("E_TODO_CREATED", path, f"TODO on line {index + 1} has no Created date")
                for name in ("Created", "Due", "Completed"):
                    if name in todo_fields:
                        try:
                            date.fromisoformat(todo_fields[name])
                        except ValueError:
                            self.add("E_TODO_DATE", path, f"{name} on line {index + 1} must be YYYY-MM-DD")
                if checked and "Completed" not in todo_fields:
                    self.add("E_TODO_COMPLETED", path, f"checked TODO on line {index + 1} has no Completed date")
            for link_value in LINK_RE.findall(text):
                self.safe_target(path, link_value, "E_STATE_LINK")
        if not found:
            self.add("E_STATE_MISSING", "state", "at least one synthetic State is required")

    def validate_unresolved_tokens(self) -> None:
        paths = [self.root / "user_config.md"]
        paths.extend((self.root / "events").glob("*/*/*/metadata.md"))
        paths.extend((self.root / "deltas").glob("*/*/*.md"))
        paths.extend((self.root / "state").glob("*.md"))
        for path in paths:
            if path.is_file() and TOKEN_RE.search(path.read_text(encoding="utf-8")):
                self.add("E_TEMPLATE_TOKEN", path, "unresolved template token remains")

    def run(self) -> list[Problem]:
        self.validate_required_paths()
        if self.problems:
            return sorted(self.problems)
        context_contract = self.load_json(self.contracts / "context_files.json")
        self.validate_versions()
        self.validate_ownership()
        self.validate_hook()
        self.validate_user_config()
        self.validate_events(context_contract)
        self.validate_deltas(context_contract)
        self.validate_states()
        self.validate_unresolved_tokens()
        return sorted(self.problems)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    validator = Validator(args.workspace)
    problems = validator.run()
    if problems:
        for problem in problems:
            print(f"{problem.code} {problem.path}: {problem.message}")
        raise SystemExit(1)
    print(f"OK {validator.root}")


if __name__ == "__main__":
    main()
