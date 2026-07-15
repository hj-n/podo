#!/usr/bin/env python3
"""Apply verified Podo inbox captures to Event, Delta, and State files."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from transaction_store import TransactionError, TransactionManager


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,79}$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$", re.MULTILINE)
TODO_RE = re.compile(r"^- \[([ xX])\]\s+(.+)$")
TODO_FIELD_RE = re.compile(r"^\s+- (Created|Due|Completed|Cancelled|Reopened|Result):\s*(.+)$")
TOKEN_RE = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
CONFIDENCE_VALUES = {"confirmed", "inferred", "needs-confirmation"}


class ContextError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class UpdatePlan:
    state_slug: str
    state_path: Path
    delta_path: Path
    delta_text: str
    state_text: str
    existing_state: bytes | None
    existing_mode: int


def fail(code: str, detail: str) -> None:
    raise ContextError(code, detail)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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


def one_line(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text or "\n" in text or "\r" in text or TOKEN_RE.search(text):
        fail("E_REQUEST_FIELD", f"{field} must be one explicit line")
    return text


def relative_link(source: Path, target: Path) -> str:
    return Path(os.path.relpath(target, source.parent)).as_posix()


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(code, str(error))
    if not isinstance(value, dict):
        fail(code, "JSON root must be an object")
    return value


class ContextStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.work = self.root / ".podo-work"
        self.inbox = self.work / "inbox"
        self.deferred = self.work / "deferred"
        self.receipts = self.work / "receipts"
        self.validator = self.root / ".podo/scripts/validate_workspace.py"

    def validate_workspace(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.validator), str(self.root), "--mode", "context-present"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode:
            fail("E_WORKSPACE_INVALID", " ".join(result.stdout.strip().splitlines()))

    def receipt_path(self, capture_id: str) -> Path:
        return self.receipts / f"{capture_id}.json"

    def ensure_receipt_is_final(self, receipt: dict[str, Any]) -> None:
        transaction_id = receipt.get("transaction_id")
        if not isinstance(transaction_id, str):
            return
        try:
            directory = TransactionManager(self.root).transaction_dir(transaction_id)
        except TransactionError as error:
            fail(error.code, error.detail)
        if directory.is_dir() and not directory.is_symlink():
            fail("E_TRANSACTION_PENDING", transaction_id)

    def deferred_path(self, capture_id: str) -> Path:
        self.capture_dir(capture_id)
        return self.deferred / f"{capture_id}.json"

    def capture_dir(self, capture_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9-]+--[A-Za-z0-9-]+", capture_id):
            fail("E_CAPTURE_ID", "capture ID has an unsupported shape")
        return self.inbox / capture_id

    def load_capture(self, capture_id: str) -> tuple[Path, dict[str, Any], Path]:
        directory = self.capture_dir(capture_id)
        if directory.is_symlink() or not directory.is_dir():
            fail("E_CAPTURE_MISSING", capture_id)
        metadata = load_json(directory / "capture.json", "E_CAPTURE_INVALID")
        original = directory / str(metadata.get("original_entrypoint", ""))
        if original.is_symlink() or not original.is_file():
            fail("E_CAPTURE_INVALID", "original entrypoint is missing")
        if metadata.get("capture_id") != capture_id:
            fail("E_CAPTURE_INVALID", "capture identity mismatch")
        try:
            actual_hash = sha256_file(original)
        except OSError as error:
            fail("E_CAPTURE_INVALID", str(error))
        if actual_hash != metadata.get("sha256"):
            fail("E_CAPTURE_INVALID", "original hash mismatch")
        return directory, metadata, original

    def list_inbox(self) -> list[dict[str, Any]]:
        if not self.inbox.exists():
            return []
        if self.inbox.is_symlink() or not self.inbox.is_dir():
            fail("E_INBOX_INVALID", ".podo-work/inbox must be a directory")
        values: list[dict[str, Any]] = []
        for directory in sorted(path for path in self.inbox.iterdir() if path.is_dir() and not path.name.startswith(".")):
            capture_id = directory.name
            if self.receipt_path(capture_id).exists() or self.deferred_path(capture_id).exists():
                continue
            _, metadata, _ = self.load_capture(capture_id)
            values.append(
                {
                    "capture_id": capture_id,
                    "occurred": metadata.get("occurred"),
                    "runtime_version": metadata.get("runtime_version"),
                    "completeness": metadata.get("completeness"),
                    "missing_record_families": metadata.get("missing_record_families", []),
                    "user_preview": metadata.get("user_preview", ""),
                    "capture_metadata": str((directory / "capture.json").relative_to(self.root)),
                    "review_entrypoint": str((directory / metadata["review_entrypoint"]).relative_to(self.root)),
                    "original_entrypoint": str((directory / metadata["original_entrypoint"]).relative_to(self.root)),
                }
            )
        return values

    def list_deferred(self) -> list[dict[str, Any]]:
        if not self.deferred.exists():
            return []
        if self.deferred.is_symlink() or not self.deferred.is_dir():
            fail("E_DEFERRED_INVALID", ".podo-work/deferred must be a directory")
        values: list[dict[str, Any]] = []
        for path in sorted(self.deferred.glob("*.json")):
            if path.is_symlink() or not path.is_file():
                fail("E_DEFERRED_INVALID", path.name)
            value = load_json(path, "E_DEFERRED_INVALID")
            capture_id = str(value.get("capture_id") or "")
            if path != self.deferred_path(capture_id):
                fail("E_DEFERRED_INVALID", f"deferred identity mismatch: {path.name}")
            if self.receipt_path(capture_id).exists():
                continue
            self.load_capture(capture_id)
            values.append(value)
        return values

    def load_deferred(
        self, capture_id: str
    ) -> tuple[Path, dict[str, Any], Path, dict[str, Any], Path]:
        path = self.deferred_path(capture_id)
        if path.is_symlink() or not path.is_file():
            fail("E_DEFERRED_MISSING", capture_id)
        value = load_json(path, "E_DEFERRED_INVALID")
        if value.get("capture_id") != capture_id:
            fail("E_DEFERRED_INVALID", "deferred identity mismatch")
        capture_dir, capture, original = self.load_capture(capture_id)
        if capture.get("completeness") != "complete-local-transcript":
            fail("E_CAPTURE_PARTIAL", ",".join(capture.get("missing_record_families") or []))
        return path, value, capture_dir, capture, original

    def validate_request_path(self, path: Path) -> Path:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.work.resolve())
        except ValueError:
            fail("E_REQUEST_PATH", "request must be inside .podo-work")
        if path.is_symlink() or not path.is_file():
            fail("E_REQUEST_PATH", "request must be an existing regular file")
        return resolved

    def event_paths(self, metadata: dict[str, Any]) -> tuple[Path, str, datetime]:
        try:
            occurred = datetime.fromisoformat(str(metadata["occurred"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            fail("E_CAPTURE_INVALID", "Occurred must be RFC3339")
        if occurred.tzinfo is None:
            fail("E_CAPTURE_INVALID", "Occurred must include timezone")
        turn_id = str(metadata.get("source", {}).get("turn_id", ""))
        safe_turn = re.sub(r"[^a-z0-9]", "", turn_id.lower())[:12] or "turn"
        identity_hash = hashlib.sha256(str(metadata["capture_id"]).encode("utf-8")).hexdigest()[:8]
        name = f"{occurred.strftime('%Y-%m-%d_%H%M%S')}-codex-{safe_turn}-{identity_hash}"
        return self.root / f"events/{occurred:%Y}/{occurred:%m}/{name}", name, occurred

    def render_event(
        self,
        capture: dict[str, Any],
        original: Path,
        event_request: dict[str, Any],
        resolution: tuple[str, str, dict[str, Any], Path] | None = None,
    ) -> str:
        title = one_line(event_request.get("title"), "event.title")
        context = str(event_request.get("context") or "").strip()
        if not context or TOKEN_RE.search(context):
            fail("E_REQUEST_FIELD", "event.context must be explicit")
        source = capture.get("source")
        if not isinstance(source, dict):
            fail("E_CAPTURE_INVALID", "source is missing")
        missing = capture.get("missing_record_families") or []
        missing_value = ", ".join(str(value) for value in missing) if missing else "none"
        lines = [
            f"# {title}",
            "",
            f"Occurred: {capture['occurred']}",
            f"Captured: {capture['captured']}",
            "Source-Type: codex-local-transcript",
            f"Source-Identity: session:{source['session_id']}#turn:{source['turn_id']}",
            f"Source-Entrypoint: {source['transcript_path']}",
            "Capture-Method: podo-stop-hook-inbox-v1",
            f"Runtime-Version: {capture['runtime_version']}",
            f"Completeness: {capture['completeness']}",
            f"Missing-Record-Families: {missing_value}",
            f"SHA-256: {sha256_file(original)}",
            "Original-Entrypoint: ./original/session.jsonl",
        ]
        if resolution is not None:
            deferred_id, decision, deferred, related_original = resolution
            lines.extend(
                [
                    f"Resolution: {decision}",
                    f"Resolves-Capture: {deferred_id}",
                    f"Deferred-Summary: {deferred['summary']}",
                    f"Related-Original: ./original/related/{deferred_id}/session.jsonl",
                    f"Related-SHA-256: {sha256_file(related_original)}",
                ]
            )
        lines.extend(
            [
                "",
                "## Context",
                "",
                context,
                "",
                "## Safety",
                "",
                "이 original은 capture 시점의 immutable snapshot이다. 누락 범위가 있으면 Metadata에 명시한다.",
                "",
            ]
        )
        return "\n".join(lines)

    def validate_state_text(self, text: str, state_slug: str) -> None:
        if text.count("{{DELTA_LINK}}") != 1:
            fail("E_REQUEST_STATE_LINK", f"{state_slug} must contain exactly one {{{{DELTA_LINK}}}} token")
        other_tokens = [token for token in TOKEN_RE.findall(text) if token != "{{DELTA_LINK}}"]
        if other_tokens:
            fail("E_REQUEST_TOKEN", f"{state_slug} has unresolved template tokens")
        fields = {match.group(1): match.group(2).strip() for match in FIELD_RE.finditer(text)}
        try:
            date.fromisoformat(fields["Updated"])
        except (KeyError, ValueError):
            fail("E_REQUEST_INVALID_DATE", f"{state_slug} Updated must be YYYY-MM-DD")
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
                fail("E_REQUEST_INVALID_DATE", f"{state_slug} TODO line {index + 1} requires Created")
            parsed_dates: dict[str, date] = {}
            for name in ("Created", "Due", "Completed", "Cancelled", "Reopened"):
                if name in todo_fields:
                    try:
                        parsed_dates[name] = date.fromisoformat(todo_fields[name])
                    except ValueError:
                        fail("E_REQUEST_INVALID_DATE", f"{state_slug} {name} must be YYYY-MM-DD")
            terminal = {name for name in ("Completed", "Cancelled") if name in todo_fields}
            if checked and len(terminal) != 1:
                fail(
                    "E_REQUEST_TODO_LIFECYCLE",
                    f"{state_slug} checked TODO requires exactly one of Completed or Cancelled",
                )
            if not checked and terminal and "Reopened" not in todo_fields:
                fail(
                    "E_REQUEST_TODO_LIFECYCLE",
                    f"{state_slug} open TODO with a terminal date requires Reopened",
                )
            created = parsed_dates.get("Created")
            for name in ("Completed", "Cancelled", "Reopened"):
                if created is not None and parsed_dates.get(name, created) < created:
                    fail("E_REQUEST_TODO_LIFECYCLE", f"{state_slug} {name} cannot precede Created")
            prior_terminal = parsed_dates.get("Completed") or parsed_dates.get("Cancelled")
            reopened = parsed_dates.get("Reopened")
            if prior_terminal is not None and reopened is not None and reopened < prior_terminal:
                fail("E_REQUEST_TODO_LIFECYCLE", f"{state_slug} Reopened cannot precede its terminal date")

    def build_plans(
        self,
        request: dict[str, Any],
        capture: dict[str, Any],
        event_metadata_path: Path,
        occurred: datetime,
    ) -> list[UpdatePlan]:
        updates = request.get("updates")
        if not isinstance(updates, list) or not updates:
            fail("E_REQUEST_FIELD", "updates must contain at least one State update")
        plans: list[UpdatePlan] = []
        seen: set[str] = set()
        for index, update in enumerate(updates, start=1):
            if not isinstance(update, dict):
                fail("E_REQUEST_FIELD", f"updates[{index}] must be an object")
            state_slug = str(update.get("state_slug") or "")
            if not SLUG_RE.fullmatch(state_slug) or state_slug in seen:
                fail("E_REQUEST_STATE", f"invalid or duplicate state_slug: {state_slug}")
            seen.add(state_slug)
            confidence = str(update.get("confidence") or "")
            if confidence not in CONFIDENCE_VALUES:
                fail("E_REQUEST_FIELD", f"invalid confidence for {state_slug}")
            if confidence != "confirmed":
                fail(
                    "E_REQUEST_CONFIDENCE",
                    f"{state_slug} cannot apply inference or unconfirmed content to current State",
                )
            state_text = str(update.get("state_markdown") or "")
            self.validate_state_text(state_text, state_slug)
            state_path = self.root / f"state/{state_slug}.md"
            if state_path.is_symlink():
                fail("E_REQUEST_STATE", f"State is a symlink: {state_slug}")
            existing_state = state_path.read_bytes() if state_path.is_file() else None
            expected = update.get("expected_state_sha256")
            if existing_state is None:
                if expected not in (None, ""):
                    fail("E_STATE_STALE", f"new State {state_slug} must use null expected hash")
                existing_mode = 0o644
            else:
                actual = sha256_bytes(existing_state)
                if expected != actual:
                    fail("E_STATE_STALE", f"State changed before apply: {state_slug}")
                existing_mode = stat.S_IMODE(state_path.stat().st_mode)

            identity = hashlib.sha256(f"{capture['capture_id']}:{state_slug}".encode("utf-8")).hexdigest()[:8]
            delta_name = f"{occurred.strftime('%Y-%m-%d_%H%M%S')}-{state_slug}-{identity}.md"
            delta_path = self.root / f"deltas/{occurred:%Y}/{occurred:%m}/{delta_name}"
            if delta_path.exists() or delta_path.is_symlink():
                fail("E_DELTA_COLLISION", delta_path.relative_to(self.root).as_posix())
            event_link = relative_link(delta_path, event_metadata_path)
            state_link = relative_link(delta_path, state_path)
            delta_text = "\n".join(
                [
                    f"# {one_line(update.get('delta_title'), f'{state_slug}.delta_title')}",
                    "",
                    f"Occurred: {capture['occurred']}",
                    f"Based-On: [Event metadata]({event_link})",
                    f"Affects: [State]({state_link})",
                    f"Confidence: {confidence}",
                    "",
                    "## Changed",
                    "",
                    str(update.get("changed") or "").strip(),
                    "",
                    "## Why",
                    "",
                    str(update.get("why") or "").strip(),
                    "",
                    "## Needs Confirmation",
                    "",
                    str(update.get("needs_confirmation") or "- 없음").strip(),
                    "",
                ]
            )
            if TOKEN_RE.search(delta_text) or not str(update.get("changed") or "").strip() or not str(update.get("why") or "").strip():
                fail("E_REQUEST_FIELD", f"{state_slug} Delta fields must be explicit")
            delta_link = relative_link(state_path, delta_path)
            rendered_state = state_text.replace("{{DELTA_LINK}}", delta_link)
            if TOKEN_RE.search(rendered_state):
                fail("E_REQUEST_TOKEN", f"{state_slug} has unresolved tokens")
            if not rendered_state.endswith("\n"):
                rendered_state += "\n"
            plans.append(
                UpdatePlan(
                    state_slug=state_slug,
                    state_path=state_path,
                    delta_path=delta_path,
                    delta_text=delta_text,
                    state_text=rendered_state,
                    existing_state=existing_state,
                    existing_mode=existing_mode,
                )
            )
        return plans

    def write_receipt(self, capture: dict[str, Any], outcome: str, **extra: Any) -> Path:
        receipt = {
            "receipt_version": 1,
            "capture_id": capture["capture_id"],
            "source": capture["source"],
            "outcome": outcome,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
        path = self.receipt_path(str(capture["capture_id"]))
        atomic_json(path, receipt)
        return path

    def defer_capture(self, capture_id: str, request_path: Path) -> dict[str, Any]:
        existing_receipt = self.receipt_path(capture_id)
        if existing_receipt.exists():
            return {"status": "already-processed", "receipt": load_json(existing_receipt, "E_RECEIPT_INVALID")}
        deferred_path = self.deferred_path(capture_id)
        if deferred_path.exists():
            return {"status": "already-deferred", "deferred": load_json(deferred_path, "E_DEFERRED_INVALID")}
        _, capture, _ = self.load_capture(capture_id)
        if capture.get("completeness") != "complete-local-transcript":
            fail("E_CAPTURE_PARTIAL", ",".join(capture.get("missing_record_families") or []))
        request_resolved = self.validate_request_path(request_path)
        request = load_json(request_resolved, "E_REQUEST_JSON")
        state_candidates = request.get("state_candidates", [])
        if not isinstance(state_candidates, list) or any(
            not isinstance(value, str) or not SLUG_RE.fullmatch(value) for value in state_candidates
        ):
            fail("E_REQUEST_STATE", "state_candidates must contain State slugs")
        if len(state_candidates) != len(set(state_candidates)):
            fail("E_REQUEST_STATE", "state_candidates must not contain duplicates")
        value = {
            "deferred_version": 1,
            "capture_id": capture_id,
            "source": capture["source"],
            "occurred": capture["occurred"],
            "deferred_at": datetime.now(timezone.utc).isoformat(),
            "summary": one_line(request.get("summary"), "summary"),
            "why_confirmation": one_line(request.get("why_confirmation"), "why_confirmation"),
            "question": one_line(request.get("question"), "question"),
            "state_candidates": state_candidates,
        }
        atomic_json(deferred_path, value)
        try:
            request_resolved.unlink()
        except OSError:
            pass
        return {
            "status": "deferred",
            "capture_id": capture_id,
            "deferred": str(deferred_path.relative_to(self.root)),
        }

    def apply(
        self,
        capture_id: str,
        request_path: Path,
        *,
        resolution: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        existing_receipt = self.receipt_path(capture_id)
        if existing_receipt.exists():
            receipt = load_json(existing_receipt, "E_RECEIPT_INVALID")
            self.ensure_receipt_is_final(receipt)
            return {"status": "already-processed", "receipt": receipt}
        if self.deferred_path(capture_id).exists():
            fail("E_CAPTURE_DEFERRED", "resolve a deferred capture with a later user turn")
        self.validate_workspace()
        capture_dir, capture, original = self.load_capture(capture_id)
        if capture.get("completeness") != "complete-local-transcript":
            fail("E_CAPTURE_PARTIAL", ",".join(capture.get("missing_record_families") or []))
        request_resolved = self.validate_request_path(request_path)
        request = load_json(request_resolved, "E_REQUEST_JSON")
        event_request = request.get("event")
        if not isinstance(event_request, dict):
            fail("E_REQUEST_FIELD", "event must be an object")
        event_dir, _, occurred = self.event_paths(capture)
        if event_dir.exists() or event_dir.is_symlink():
            fail("E_EVENT_COLLISION", event_dir.relative_to(self.root).as_posix())
        event_metadata_path = event_dir / "metadata.md"
        resolution_context: tuple[str, str, dict[str, Any], Path] | None = None
        deferred_path: Path | None = None
        deferred_capture_dir: Path | None = None
        deferred_capture: dict[str, Any] | None = None
        if resolution is not None:
            deferred_id, decision = resolution
            if deferred_id == capture_id or decision not in {"confirmed", "rejected"}:
                fail("E_RESOLUTION", "resolution identity or decision is invalid")
            if self.receipt_path(deferred_id).exists():
                fail("E_RESOLUTION", "deferred capture is already resolved")
            deferred_path, deferred, deferred_capture_dir, deferred_capture, related_original = self.load_deferred(
                deferred_id
            )
            resolution_context = (deferred_id, decision, deferred, related_original)
        event_text = self.render_event(capture, original, event_request, resolution_context)
        plans = self.build_plans(request, capture, event_metadata_path, occurred)
        processed_at = datetime.now(timezone.utc).isoformat()
        current_receipt = {
            "receipt_version": 1,
            "capture_id": capture["capture_id"],
            "source": capture["source"],
            "outcome": "applied",
            "processed_at": processed_at,
            "event": str(event_metadata_path.relative_to(self.root)),
            "deltas": [str(plan.delta_path.relative_to(self.root)) for plan in plans],
            "states": [str(plan.state_path.relative_to(self.root)) for plan in plans],
            **(
                {"resolution_of": resolution_context[0], "resolution": resolution_context[1]}
                if resolution_context is not None
                else {}
            ),
        }
        receipts: list[tuple[Path, dict[str, Any]]] = [(self.receipt_path(capture_id), current_receipt)]
        if resolution_context is not None and deferred_capture is not None:
            receipts.append(
                (
                    self.receipt_path(str(deferred_capture["capture_id"])),
                    {
                        "receipt_version": 1,
                        "capture_id": deferred_capture["capture_id"],
                        "source": deferred_capture["source"],
                        "outcome": resolution_context[1],
                        "processed_at": processed_at,
                        "resolved_by_capture": capture_id,
                        "event": str(event_metadata_path.relative_to(self.root)),
                    },
                )
            )
        cleanup: list[tuple[str, Path]] = [("dir", capture_dir), ("file", request_resolved)]
        if deferred_capture_dir is not None:
            cleanup.append(("dir", deferred_capture_dir))
        if deferred_path is not None:
            cleanup.append(("file", deferred_path))
        transaction = TransactionManager(self.root)
        try:
            transaction_id = transaction.prepare_context_apply(
                capture_id=capture_id,
                event_target=event_dir,
                event_metadata=event_text,
                primary_original=original,
                related_originals=(
                    [(resolution_context[0], resolution_context[3])]
                    if resolution_context is not None
                    else []
                ),
                updates=[
                    {
                        "state_slug": plan.state_slug,
                        "delta_target": plan.delta_path,
                        "delta_text": plan.delta_text,
                        "state_target": plan.state_path,
                        "state_text": plan.state_text,
                        "existing_state": plan.existing_state,
                        "mode": plan.existing_mode,
                    }
                    for plan in plans
                ],
                receipts=receipts,
                cleanup=cleanup,
            )
            transaction_result = transaction.commit(transaction_id, self.validate_workspace)
        except TransactionError as error:
            fail(error.code, error.detail)
        return {
            "status": "applied",
            "event": str(event_metadata_path.relative_to(self.root)),
            "deltas": [str(plan.delta_path.relative_to(self.root)) for plan in plans],
            "states": [str(plan.state_path.relative_to(self.root)) for plan in plans],
            "receipt": str(self.receipt_path(capture_id).relative_to(self.root)),
            "transaction": transaction_result["transaction_id"],
            **({"resolved_deferred": resolution_context[0]} if resolution_context is not None else {}),
        }

    def discard(self, capture_id: str, reason: str) -> dict[str, Any]:
        if reason not in {"no-delta", "sensitive-data"}:
            fail("E_DISCARD_REASON", "unsupported discard reason")
        existing_receipt = self.receipt_path(capture_id)
        if existing_receipt.exists():
            return {"status": "already-processed", "receipt": load_json(existing_receipt, "E_RECEIPT_INVALID")}
        if self.deferred_path(capture_id).exists():
            fail("E_CAPTURE_DEFERRED", "resolve a deferred capture instead of discarding it directly")
        capture_dir, capture, _ = self.load_capture(capture_id)
        trash = self.work / f".discard-{capture_id}"
        if trash.exists():
            fail("E_DISCARD_COLLISION", trash.name)
        os.replace(capture_dir, trash)
        try:
            outcome = "no-delta" if reason == "no-delta" else "sensitive-data-excluded"
            receipt_path = self.write_receipt(capture, outcome, reason=reason)
        except Exception:
            os.replace(trash, capture_dir)
            raise
        shutil.rmtree(trash)
        return {
            "status": "discarded",
            "outcome": outcome,
            "receipt": str(receipt_path.relative_to(self.root)),
        }

    def resolve(
        self,
        deferred_id: str,
        capture_id: str,
        decision: str,
        request_path: Path | None,
    ) -> dict[str, Any]:
        if deferred_id == capture_id or decision not in {"confirmed", "rejected"}:
            fail("E_RESOLUTION", "resolution identity or decision is invalid")
        deferred_receipt = self.receipt_path(deferred_id)
        if deferred_receipt.exists():
            receipt = load_json(deferred_receipt, "E_RECEIPT_INVALID")
            self.ensure_receipt_is_final(receipt)
            return {"status": "already-resolved", "receipt": receipt}
        self.load_deferred(deferred_id)
        if decision == "confirmed" and request_path is None:
            fail("E_RESOLUTION_REQUEST", "confirmed resolution requires a Context apply request")
        if request_path is not None:
            return self.apply(capture_id, request_path, resolution=(deferred_id, decision))

        current_receipt = self.receipt_path(capture_id)
        if current_receipt.exists():
            fail("E_RESOLUTION", "resolution capture is already processed")
        current_dir, current_capture, _ = self.load_capture(capture_id)
        if current_capture.get("completeness") != "complete-local-transcript":
            fail("E_CAPTURE_PARTIAL", ",".join(current_capture.get("missing_record_families") or []))
        deferred_path, _, deferred_dir, deferred_capture, _ = self.load_deferred(deferred_id)
        current_trash = self.work / f".resolve-current-{capture_id}"
        deferred_trash = self.work / f".resolve-deferred-{deferred_id}"
        if current_trash.exists() or deferred_trash.exists():
            fail("E_RESOLUTION_COLLISION", "resolution staging path already exists")
        os.replace(current_dir, current_trash)
        try:
            os.replace(deferred_dir, deferred_trash)
        except Exception:
            os.replace(current_trash, current_dir)
            raise
        try:
            current_receipt_path = self.write_receipt(
                current_capture,
                "no-delta",
                resolution_of=deferred_id,
                resolution="rejected",
            )
            self.write_receipt(
                deferred_capture,
                "rejected",
                resolved_by_capture=capture_id,
                permanent_context_changed=False,
            )
            deferred_path.unlink()
        except Exception:
            try:
                current_receipt.unlink()
            except OSError:
                pass
            try:
                deferred_receipt.unlink()
            except OSError:
                pass
            os.replace(deferred_trash, deferred_dir)
            os.replace(current_trash, current_dir)
            raise
        shutil.rmtree(current_trash)
        shutil.rmtree(deferred_trash)
        return {
            "status": "rejected",
            "resolved_deferred": deferred_id,
            "permanent_context_changed": False,
            "receipt": str(current_receipt_path.relative_to(self.root)),
        }
