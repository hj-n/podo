#!/usr/bin/env python3
"""Versioned adapter for the local Codex JSONL transcript used by Podo."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_RUNTIMES = {"0.144.0-alpha.4", "0.145.0-alpha.18"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,127}$")


class AdapterError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class TranscriptInfo:
    runtime_version: str
    session_id: str
    turn_id: str
    occurred: str
    completeness: str
    missing_record_families: tuple[str, ...]
    observed_record_families: tuple[str, ...]
    observed_record_types: tuple[str, ...]
    user_preview: str


def fail(code: str, detail: str) -> None:
    raise AdapterError(code, detail)


def normalize_runtime(value: Any) -> str:
    runtime = str(value or "").strip()
    if runtime.startswith("codex-cli "):
        runtime = runtime.removeprefix("codex-cli ")
    return runtime


def parse_timestamp(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.isoformat()


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        value = item.get("text") or item.get("input_text") or item.get("output_text")
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def classify(record: dict[str, Any]) -> tuple[str | None, str]:
    top_type = str(record.get("type", "unknown"))
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None, top_type
    payload_type = str(payload.get("type", ""))
    if top_type == "response_item":
        if payload_type == "message":
            role = payload.get("role")
            if role == "user":
                return "user_message", f"{top_type}:{payload_type}:user"
            if role == "assistant":
                return "assistant_message", f"{top_type}:{payload_type}:assistant"
        if payload_type in {
            "function_call",
            "custom_tool_call",
            "local_shell_call",
            "computer_call",
            "web_search_call",
        }:
            return "tool_call", f"{top_type}:{payload_type}"
        if payload_type in {
            "function_call_output",
            "custom_tool_call_output",
            "local_shell_call_output",
            "computer_call_output",
            "web_search_call_output",
        }:
            return "tool_result", f"{top_type}:{payload_type}"
    if top_type == "event_msg":
        if payload_type == "user_message":
            return "user_message", f"{top_type}:{payload_type}"
        if payload_type in {"agent_message", "assistant_message"}:
            return "assistant_message", f"{top_type}:{payload_type}"
    if top_type in {"user_message", "assistant_message", "tool_call", "tool_result"}:
        return top_type, top_type
    return None, f"{top_type}:{payload_type}" if payload_type else top_type


def payload_has_turn(record: dict[str, Any], turn_id: str) -> bool:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return False
    for key in ("turn_id", "turnId"):
        if payload.get(key) == turn_id:
            return True
    if record.get("type") == "turn_context" and payload.get("id") == turn_id:
        return True
    return False


def user_text(record: dict[str, Any]) -> str:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return ""
    if record.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
        return text_from_content(payload.get("content"))
    if record.get("type") == "event_msg" and payload.get("type") == "user_message":
        return str(payload.get("message") or payload.get("text") or "")
    return ""


def parse_transcript(raw: bytes, expected_session_id: str, expected_turn_id: str) -> TranscriptInfo:
    if not ID_RE.fullmatch(expected_session_id):
        fail("PODO_CAPTURE_INVALID_ID", "session_id has an unsupported shape")
    if not ID_RE.fullmatch(expected_turn_id):
        fail("PODO_CAPTURE_INVALID_ID", "turn_id has an unsupported shape")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        fail("PODO_CAPTURE_INVALID_TRANSCRIPT", f"transcript is not UTF-8: {error}")

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            fail("PODO_CAPTURE_INVALID_TRANSCRIPT", f"line {line_number}: {error}")
        if not isinstance(record, dict):
            fail("PODO_CAPTURE_INVALID_TRANSCRIPT", f"line {line_number}: record must be an object")
        records.append(record)
    if not records:
        fail("PODO_CAPTURE_INVALID_TRANSCRIPT", "transcript has no records")

    session_records = [record for record in records if record.get("type") == "session_meta"]
    if not session_records:
        fail("PODO_CAPTURE_SESSION_MISSING", "session_meta record is missing")
    session_payload = session_records[0].get("payload")
    if not isinstance(session_payload, dict):
        fail("PODO_CAPTURE_SESSION_MISSING", "session_meta payload is invalid")
    source_session = str(session_payload.get("id") or "")
    if source_session != expected_session_id:
        fail(
            "PODO_CAPTURE_SESSION_MISMATCH",
            f"hook session {expected_session_id} does not match transcript session {source_session or '<missing>'}",
        )
    runtime = normalize_runtime(session_payload.get("cli_version") or session_payload.get("runtime_version"))
    if runtime not in SUPPORTED_RUNTIMES:
        fail("PODO_CAPTURE_UNSUPPORTED_RUNTIME", runtime or "runtime version is missing")

    turn_records = [record for record in records if payload_has_turn(record, expected_turn_id)]
    if not turn_records:
        fail("PODO_CAPTURE_TURN_MISSING", f"turn not found in transcript: {expected_turn_id}")

    families: set[str] = set()
    record_types: set[str] = set()
    previews: list[str] = []
    last_timestamp: str | None = None
    turn_timestamp: str | None = None
    for record in records:
        family, record_type = classify(record)
        record_types.add(record_type)
        if family:
            families.add(family)
        preview = user_text(record).strip()
        if preview:
            previews.append(preview)
        timestamp = parse_timestamp(record.get("timestamp"))
        if timestamp:
            last_timestamp = timestamp
            if payload_has_turn(record, expected_turn_id) and turn_timestamp is None:
                turn_timestamp = timestamp

    missing: list[str] = []
    for required in ("user_message", "assistant_message"):
        if required not in families:
            missing.append(required)
    if "tool_call" in families and "tool_result" not in families:
        missing.append("tool_result")
    if "tool_result" in families and "tool_call" not in families:
        missing.append("tool_call")
    completeness = "complete-local-transcript" if not missing else "partial"
    occurred = turn_timestamp or last_timestamp or datetime.now(timezone.utc).isoformat()
    preview = " ".join(previews[-1].split())[:240] if previews else ""
    return TranscriptInfo(
        runtime_version=runtime,
        session_id=source_session,
        turn_id=expected_turn_id,
        occurred=occurred,
        completeness=completeness,
        missing_record_families=tuple(sorted(set(missing))),
        observed_record_families=tuple(sorted(families)),
        observed_record_types=tuple(sorted(record_types)),
        user_preview=preview,
    )


def extract_turn_jsonl(raw: bytes, expected_turn_id: str) -> bytes:
    """Return the exact JSONL lines belonging to one turn_context span."""
    lines = raw.splitlines(keepends=True)
    start: int | None = None
    end = len(lines)
    for index, line in enumerate(lines):
        try:
            record = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict) or record.get("type") != "turn_context":
            continue
        if start is None and payload_has_turn(record, expected_turn_id):
            start = index
            continue
        if start is not None:
            end = index
            break
    if start is None:
        fail("PODO_CAPTURE_TURN_MISSING", f"turn_context not found: {expected_turn_id}")
    return b"".join(lines[start:end])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--turn-id", required=True)
    args = parser.parse_args()
    try:
        info = parse_transcript(args.transcript.read_bytes(), args.session_id, args.turn_id)
    except (OSError, AdapterError) as error:
        if isinstance(error, AdapterError):
            print(f"ERROR {error.code} {error.detail}")
        else:
            print(f"ERROR PODO_CAPTURE_SOURCE_UNREADABLE {error}")
        raise SystemExit(1)
    print(json.dumps(info.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
