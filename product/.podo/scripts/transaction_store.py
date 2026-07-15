#!/usr/bin/env python3
"""Prepare and commit journaled Podo Context transactions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class TransactionError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> None:
    raise TransactionError(code, detail)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.is_dir() or path.is_symlink():
        fail("E_TRANSACTION_PATH", f"not a regular directory: {path}")
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        if child.is_symlink():
            fail("E_TRANSACTION_PATH", f"symlink in transaction tree: {child}")
        relative = child.relative_to(path).as_posix().encode("utf-8")
        raw = child.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(code, str(error))
    if not isinstance(value, dict):
        fail(code, "JSON root must be an object")
    return value


def atomic_copy(source: Path, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with source.open("rb") as reader, os.fdopen(descriptor, "wb") as writer:
            shutil.copyfileobj(reader, writer)
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


class TransactionManager:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.work = self.root / ".podo-work"
        self.transactions = self.work / "transactions"
        self.transaction_receipts = self.work / "transaction-receipts"

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            fail("E_TRANSACTION_PATH", f"path escapes Workspace: {path}")

    def rooted(self, value: str) -> Path:
        if not value or value.startswith("/") or ".." in Path(value).parts:
            fail("E_TRANSACTION_PATH", f"unsafe relative path: {value}")
        path = (self.root / value).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            fail("E_TRANSACTION_PATH", f"path escapes Workspace: {value}")
        return path

    def transaction_id(self, capture_id: str) -> str:
        digest = hashlib.sha256(f"context-apply:{capture_id}".encode()).hexdigest()[:20]
        return f"context-{digest}"

    def transaction_dir(self, transaction_id: str) -> Path:
        if not transaction_id.startswith("context-") or len(transaction_id) != 28:
            fail("E_TRANSACTION_ID", transaction_id)
        return self.transactions / transaction_id

    def save_journal(self, directory: Path, journal: dict[str, Any]) -> None:
        journal["updated_at"] = now()
        atomic_json(directory / "journal.json", journal)

    def mark_completed(self, directory: Path, journal: dict[str, Any], step: str) -> None:
        completed = journal.setdefault("completed", [])
        if step not in completed:
            completed.append(step)
        journal["current_step"] = None
        self.save_journal(directory, journal)

    def start_step(self, directory: Path, journal: dict[str, Any], step: str) -> None:
        journal["state"] = "committing"
        journal["current_step"] = step
        self.save_journal(directory, journal)

    def inject(self, directory: Path, journal: dict[str, Any], point: str) -> None:
        if os.environ.get("PODO_TEST_FAILURES") != "1" or os.environ.get("PODO_TEST_FAIL_AT") != point:
            return
        journal["state"] = "recovery-required"
        journal["failure"] = {"code": "E_INJECTED_FAILURE", "point": point, "at": now()}
        self.save_journal(directory, journal)
        fail("E_INJECTED_FAILURE", point)

    def prepare_context_apply(
        self,
        *,
        capture_id: str,
        event_target: Path,
        event_metadata: str,
        primary_original: Path,
        related_originals: list[tuple[str, Path]],
        updates: list[dict[str, Any]],
        receipts: list[tuple[Path, dict[str, Any]]],
        cleanup: list[tuple[str, Path]],
    ) -> str:
        transaction_id = self.transaction_id(capture_id)
        directory = self.transaction_dir(transaction_id)
        if directory.exists() or directory.is_symlink():
            fail("E_TRANSACTION_PENDING", transaction_id)
        directory.mkdir(parents=True)
        staged = directory / "staged"
        originals = directory / "originals"
        try:
            event_stage = staged / "event"
            (event_stage / "original").mkdir(parents=True)
            shutil.copy2(primary_original, event_stage / "original/session.jsonl")
            related_records: list[dict[str, str]] = []
            for related_id, source in related_originals:
                target = event_stage / f"original/related/{related_id}/session.jsonl"
                target.parent.mkdir(parents=True)
                shutil.copy2(source, target)
                related_records.append(
                    {"capture_id": related_id, "staged": target.relative_to(directory).as_posix(), "sha256": sha256_file(target)}
                )
            (event_stage / "metadata.md").write_text(event_metadata, encoding="utf-8")

            deltas: list[dict[str, Any]] = []
            states: list[dict[str, Any]] = []
            for index, update in enumerate(updates):
                delta_stage = staged / f"deltas/{index}.md"
                delta_stage.parent.mkdir(parents=True, exist_ok=True)
                delta_stage.write_text(str(update["delta_text"]), encoding="utf-8")
                state_stage = staged / f"states/{update['state_slug']}.md"
                state_stage.parent.mkdir(parents=True, exist_ok=True)
                state_stage.write_text(str(update["state_text"]), encoding="utf-8")
                state_stage.chmod(int(update["mode"]))
                original_stage: str | None = None
                original_sha: str | None = None
                if update.get("existing_state") is not None:
                    original = originals / f"states/{update['state_slug']}.md"
                    original.parent.mkdir(parents=True, exist_ok=True)
                    original.write_bytes(update["existing_state"])
                    original.chmod(int(update["mode"]))
                    original_stage = original.relative_to(directory).as_posix()
                    original_sha = sha256_file(original)
                deltas.append(
                    {
                        "step": f"delta:{index}", "staged": delta_stage.relative_to(directory).as_posix(),
                        "target": self.relative(Path(update["delta_target"])), "sha256": sha256_file(delta_stage), "mode": "0644",
                    }
                )
                states.append(
                    {
                        "step": f"state:{update['state_slug']}", "state_slug": update["state_slug"],
                        "staged": state_stage.relative_to(directory).as_posix(), "target": self.relative(Path(update["state_target"])),
                        "expected_sha256": original_sha, "new_sha256": sha256_file(state_stage), "original": original_stage,
                        "mode": f"{int(update['mode']):04o}",
                    }
                )

            receipt_records: list[dict[str, Any]] = []
            for index, (target, value) in enumerate(receipts):
                value = {**value, "transaction_id": transaction_id}
                receipt_stage = staged / f"receipts/{index}.json"
                atomic_json(receipt_stage, value)
                receipt_records.append(
                    {
                        "step": f"receipt:{value['capture_id']}", "staged": receipt_stage.relative_to(directory).as_posix(),
                        "target": self.relative(target), "sha256": sha256_file(receipt_stage), "mode": "0644",
                    }
                )

            plan = {
                "transaction_version": 1, "transaction_id": transaction_id, "operation": "context-apply",
                "capture_id": capture_id, "created_at": now(),
                "event": {
                    "step": "event", "staged": event_stage.relative_to(directory).as_posix(),
                    "target": self.relative(event_target), "tree_sha256": tree_hash(event_stage),
                    "primary_sha256": sha256_file(event_stage / "original/session.jsonl"), "related_originals": related_records,
                },
                "deltas": deltas, "states": states, "receipts": receipt_records,
                "cleanup": [{"kind": kind, "path": self.relative(path)} for kind, path in cleanup],
            }
            atomic_json(directory / "plan.json", plan)
            journal = {
                "journal_version": 1, "transaction_id": transaction_id, "state": "prepared", "current_step": None,
                "completed": [], "created_at": now(), "updated_at": now(),
            }
            atomic_json(directory / "journal.json", journal)
            self.validate_prepared(directory, plan)
            self.inject(directory, journal, "after-prepared")
            return transaction_id
        except Exception as error:
            if not (directory / "plan.json").exists():
                shutil.rmtree(directory, ignore_errors=True)
            if isinstance(error, TransactionError):
                raise
            fail("E_TRANSACTION_PREPARE", str(error))

    def validate_prepared(self, directory: Path, plan: dict[str, Any]) -> None:
        event = plan["event"]
        event_stage = directory / event["staged"]
        if tree_hash(event_stage) != event["tree_sha256"] or sha256_file(event_stage / "original/session.jsonl") != event["primary_sha256"]:
            fail("E_TRANSACTION_STAGE", "staged Event mismatch")
        if "{{" in (event_stage / "metadata.md").read_text(encoding="utf-8"):
            fail("E_TRANSACTION_STAGE", "Event metadata has unresolved tokens")
        for collection in (plan["deltas"], plan["states"], plan["receipts"]):
            for entry in collection:
                staged = directory / entry["staged"]
                expected = entry.get("sha256", entry.get("new_sha256"))
                if staged.is_symlink() or not staged.is_file() or sha256_file(staged) != expected:
                    fail("E_TRANSACTION_STAGE", f"staged file mismatch: {entry['step']}")
                self.rooted(entry["target"])

    def load(self, transaction_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
        directory = self.transaction_dir(transaction_id)
        if directory.is_symlink() or not directory.is_dir():
            fail("E_TRANSACTION_MISSING", transaction_id)
        plan = load_json(directory / "plan.json", "E_TRANSACTION_PLAN")
        journal = load_json(directory / "journal.json", "E_TRANSACTION_JOURNAL")
        if plan.get("transaction_id") != transaction_id or journal.get("transaction_id") != transaction_id:
            fail("E_TRANSACTION_INVALID", "transaction identity mismatch")
        self.validate_prepared(directory, plan)
        return directory, plan, journal

    def install_directory(self, staged: Path, target: Path, expected_tree: str) -> None:
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink() and tree_hash(target) == expected_tree:
                return
            fail("E_TRANSACTION_TARGET", f"Event target collision: {self.relative(target)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
        try:
            shutil.copytree(staged, temporary, dirs_exist_ok=True)
            if tree_hash(temporary) != expected_tree:
                fail("E_TRANSACTION_COPY", "Event copy hash mismatch")
            os.replace(temporary, target)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise

    def install_file(self, staged: Path, target: Path, expected_sha: str, mode: int) -> None:
        if target.exists() or target.is_symlink():
            if target.is_file() and not target.is_symlink() and sha256_file(target) == expected_sha:
                return
            fail("E_TRANSACTION_TARGET", f"file target collision: {self.relative(target)}")
        atomic_copy(staged, target, mode)
        if sha256_file(target) != expected_sha:
            fail("E_TRANSACTION_COPY", f"file copy mismatch: {self.relative(target)}")

    def install_state(self, directory: Path, entry: dict[str, Any]) -> None:
        staged = directory / entry["staged"]
        target = self.rooted(entry["target"])
        actual = sha256_file(target) if target.is_file() and not target.is_symlink() else None
        if actual == entry["new_sha256"]:
            return
        if target.is_symlink() or (target.exists() and not target.is_file()) or actual != entry.get("expected_sha256"):
            fail("E_STATE_STALE", f"State changed before commit: {entry['state_slug']}")
        atomic_copy(staged, target, int(entry["mode"], 8))

    def cleanup_sources(self, plan: dict[str, Any]) -> None:
        for entry in plan.get("cleanup", []):
            path = self.rooted(entry["path"])
            try:
                path.relative_to(self.work.resolve())
            except ValueError:
                fail("E_TRANSACTION_CLEANUP", f"cleanup escapes .podo-work: {entry['path']}")
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_symlink():
                fail("E_TRANSACTION_CLEANUP", f"cleanup path is symlink: {entry['path']}")
            if entry["kind"] == "dir" and path.is_dir():
                shutil.rmtree(path)
            elif entry["kind"] == "file" and path.is_file():
                path.unlink()
            else:
                fail("E_TRANSACTION_CLEANUP", f"cleanup path type changed: {entry['path']}")

    def commit(self, transaction_id: str, validate_workspace: Callable[[], None]) -> dict[str, Any]:
        directory, plan, journal = self.load(transaction_id)
        completed = set(journal.get("completed", []))
        try:
            event = plan["event"]
            if event["step"] not in completed:
                self.start_step(directory, journal, event["step"])
                self.install_directory(directory / event["staged"], self.rooted(event["target"]), event["tree_sha256"])
                self.mark_completed(directory, journal, event["step"]); completed.add(event["step"])
            self.inject(directory, journal, "after-event")
            for index, entry in enumerate(plan["deltas"]):
                if entry["step"] not in completed:
                    self.start_step(directory, journal, entry["step"])
                    self.install_file(directory / entry["staged"], self.rooted(entry["target"]), entry["sha256"], int(entry["mode"], 8))
                    self.mark_completed(directory, journal, entry["step"]); completed.add(entry["step"])
                self.inject(directory, journal, f"after-delta-{index + 1}")
            self.inject(directory, journal, "before-states")
            for index, entry in enumerate(plan["states"]):
                if entry["step"] not in completed:
                    self.start_step(directory, journal, entry["step"])
                    self.install_state(directory, entry)
                    self.mark_completed(directory, journal, entry["step"]); completed.add(entry["step"])
                self.inject(directory, journal, f"after-state-{index + 1}")
            for index, entry in enumerate(plan["receipts"]):
                if entry["step"] not in completed:
                    self.start_step(directory, journal, entry["step"])
                    self.install_file(directory / entry["staged"], self.rooted(entry["target"]), entry["sha256"], int(entry["mode"], 8))
                    self.mark_completed(directory, journal, entry["step"]); completed.add(entry["step"])
                self.inject(directory, journal, f"after-receipt-{index + 1}")
            self.inject(directory, journal, "before-final-validation")
            validate_workspace()
            self.inject(directory, journal, "after-final-validation")
            self.cleanup_sources(plan)
            journal["state"] = "committed"; journal["committed_at"] = now(); self.save_journal(directory, journal)
            receipt = {
                "transaction_receipt_version": 1, "transaction_id": transaction_id, "operation": plan["operation"],
                "capture_id": plan["capture_id"], "committed_at": journal["committed_at"], "completed": journal["completed"],
            }
            receipt_path = self.transaction_receipts / f"{transaction_id}.json"
            atomic_json(receipt_path, receipt)
            shutil.rmtree(directory)
            return {"status": "committed", "transaction_id": transaction_id, "transaction_receipt": self.relative(receipt_path)}
        except Exception as error:
            try:
                journal = load_json(directory / "journal.json", "E_TRANSACTION_JOURNAL")
                journal["state"] = "recovery-required"
                if journal.get("failure", {}).get("code") != "E_INJECTED_FAILURE":
                    journal["failure"] = {
                        "code": getattr(error, "code", "E_TRANSACTION_COMMIT"),
                        "detail": str(error),
                        "at": now(),
                    }
                self.save_journal(directory, journal)
            except Exception:
                pass
            if isinstance(error, TransactionError):
                raise
            fail("E_TRANSACTION_COMMIT", str(error))

    def unfinished(self) -> list[str]:
        if not self.transactions.exists():
            return []
        if self.transactions.is_symlink() or not self.transactions.is_dir():
            fail("E_TRANSACTION_PATH", ".podo-work/transactions must be a directory")
        return sorted(path.name for path in self.transactions.iterdir() if path.is_dir() and not path.name.startswith("."))
