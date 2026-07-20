#!/usr/bin/env python3
"""Build a deterministic, synthetic Podo User Workspace for development tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOT = REPO_ROOT / "product"
TOKEN_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

EVENT_DIR = "2026-07-15_090000-synthetic-planning"
DELTA_FILE = "2026-07-15_091500-synthetic-planning.md"
STATE_FILE = "synthetic-planning.md"


def render(template: Path, values: dict[str, str]) -> str:
    content = template.read_text(encoding="utf-8")
    required = set(TOKEN_RE.findall(content))
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError(f"missing template values for {template}: {', '.join(missing)}")
    for key in required:
        content = content.replace("{{" + key + "}}", values[key])
    unresolved = TOKEN_RE.findall(content)
    if unresolved:
        raise ValueError(f"unresolved template values for {template}: {', '.join(unresolved)}")
    return content


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"output must be absent or empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(PRODUCT_ROOT / "AGENTS.podo.md", output / "AGENTS.md")
    shutil.copytree(PRODUCT_ROOT / ".codex", output / ".codex")
    shutil.copytree(
        PRODUCT_ROOT / ".podo",
        output / ".podo",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    for directory in (
        ".podo-work",
        ".podo-backups",
        "events",
        "deltas",
        "state",
        "people",
        "research/papers",
        "research/topics",
        "research/projects",
    ):
        (output / directory).mkdir(parents=True, exist_ok=True)

    shutil.copyfile(
        PRODUCT_ROOT / ".podo/templates/workspace/WORKSPACE_VERSION",
        output / "WORKSPACE_VERSION",
    )
    user_config = render(
        PRODUCT_ROOT / ".podo/templates/workspace/user_config.md",
        {
            "ASSISTANT_NAME": "포도테스트",
            "ASSISTANT_PERSONALITY": "차분하고 명확함",
            "RESPONSE_STYLE": "짧은 설명과 필요한 다음 행동",
            "EXPLICIT_DEFAULTS": "- 날짜는 ISO 형식으로 기록한다.",
            "ALLOWED_EXTERNAL_SOURCES": "- 없음. 이 fixture는 local synthetic data만 사용한다.",
        },
    )
    write(output / "user_config.md", user_config)

    original_records = [
        {
            "timestamp": "2026-07-15T09:00:00+09:00",
            "type": "user_message",
            "text": "합성 프로젝트 회의를 금요일 오전 9시에 하자.",
        },
        {
            "timestamp": "2026-07-15T09:00:01+09:00",
            "type": "assistant_message",
            "text": "금요일 오전 9시로 현재 결정을 정리할게요.",
        },
        {
            "timestamp": "2026-07-15T09:00:02+09:00",
            "type": "tool_call",
            "name": "synthetic_lookup",
        },
        {
            "timestamp": "2026-07-15T09:00:03+09:00",
            "type": "tool_result",
            "result": "synthetic-only",
        },
    ]
    original = "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in original_records
    )
    original_path = output / f"events/2026/07/{EVENT_DIR}/original/conversation.jsonl"
    write(original_path, original)
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()

    metadata = render(
        PRODUCT_ROOT / ".podo/templates/event/metadata.md",
        {
            "EVENT_TITLE": "Synthetic planning conversation",
            "OCCURRED_RFC3339": "2026-07-15T09:00:00+09:00",
            "CAPTURED_RFC3339": "2026-07-15T09:00:05+09:00",
            "SOURCE_TYPE": "synthetic-codex-conversation",
            "SOURCE_IDENTITY": "session:synthetic-001#turn:synthetic-001",
            "SOURCE_ENTRYPOINT": "synthetic://phase-1/session-001/turn-001",
            "CAPTURE_METHOD": "phase-1-fixture-builder",
            "RUNTIME_VERSION": "synthetic-fixture-1",
            "COMPLETENESS": "complete-local-transcript",
            "MISSING_RECORD_FAMILIES": "none",
            "ORIGINAL_SHA256": digest,
            "ORIGINAL_FILENAME": "conversation.jsonl",
            "EVENT_CONTEXT": "Podo 데이터 계약을 검증하기 위한 개인 정보 없는 합성 대화다.",
        },
    )
    write(output / f"events/2026/07/{EVENT_DIR}/metadata.md", metadata)

    delta = render(
        PRODUCT_ROOT / ".podo/templates/delta.md",
        {
            "DELTA_TITLE": "Synthetic meeting time decided",
            "OCCURRED_RFC3339": "2026-07-15T09:15:00+09:00",
            "EVENT_METADATA_LINK": f"../../../events/2026/07/{EVENT_DIR}/metadata.md",
            "STATE_LINK": f"../../../state/{STATE_FILE}",
            "CONFIDENCE": "confirmed",
            "CHANGED": "- 합성 프로젝트 회의를 금요일 오전 9시에 진행한다.",
            "WHY": "사용자가 합성 대화에서 시간을 명시적으로 결정했다.",
            "NEEDS_CONFIRMATION": "- 없음",
        },
    )
    write(output / f"deltas/2026/07/{DELTA_FILE}", delta)

    state = render(
        PRODUCT_ROOT / ".podo/templates/state.md",
        {
            "STATE_TITLE": "Synthetic Planning",
            "UPDATED_DATE": "2026-07-15",
            "CURRENT_CONTEXT": "Phase 1 데이터 계약을 검증하는 합성 프로젝트다.",
            "CURRENT_DECISIONS": "- 합성 프로젝트 회의는 금요일 오전 9시에 한다.",
            "TODO_TEXT": "초록색 합성 문서를 준비한다.",
            "TODO_CREATED_DATE": "2026-07-15",
            "TODO_DUE_DATE": "2026-07-17",
            "DELTA_LINK": f"../deltas/2026/07/{DELTA_FILE}",
        },
    )
    write(output / f"state/{STATE_FILE}", state)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.output.resolve())
    print(f"BUILT {args.output.resolve()}")


if __name__ == "__main__":
    main()
