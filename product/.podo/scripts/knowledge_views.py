#!/usr/bin/env python3
"""Read-only views over human-readable Podo user data."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


TODO_RE = re.compile(r"^- \[([ xX])\]\s+(.+)$")
TODO_FIELD_RE = re.compile(
    r"^\s+- (Created|Due|Target|Completed|Cancelled|Reopened|Result|Status|Priority|Time|Place|Reservation|Note):\s*(.+)$"
)
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$")
LINK_ONLY_RE = re.compile(r"^\s*-?\s*\[[^]]+\]\([^)]+\)\s*$")


class ViewError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def parse_date(value: str, field: str, path: Path) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ViewError("E_TODO_DATE", f"{path}: {field} must be YYYY-MM-DD") from error


class KnowledgeViews:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def todos(
        self,
        *,
        due_before: date | None = None,
        state: str | None = None,
        include_closed: bool = False,
    ) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        state_root = self.root / "state"
        paths = sorted(state_root.rglob("*.md")) if state_root.is_dir() else []
        for path in paths:
            relative = path.relative_to(self.root).as_posix()
            slug = path.relative_to(state_root).with_suffix("").as_posix()
            if state is not None and state not in {slug, relative, path.name}:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            for index, line in enumerate(lines):
                match = TODO_RE.match(line)
                if not match:
                    continue
                fields: dict[str, str] = {}
                for following in lines[index + 1 :]:
                    if TODO_RE.match(following) or following.startswith("## "):
                        break
                    field = TODO_FIELD_RE.match(following)
                    if field:
                        fields[field.group(1)] = field.group(2).strip()
                closed = match.group(1).lower() == "x"
                if closed and not include_closed:
                    continue
                if due_before is not None:
                    due = fields.get("Due")
                    if due is None or parse_date(due, "Due", path) > due_before:
                        continue
                values.append(
                    {
                        "text": match.group(2).strip(),
                        "closed": closed,
                        "state": slug,
                        "path": relative,
                        "line": index + 1,
                        "created": fields.get("Created"),
                        "due": fields.get("Due"),
                        "target": fields.get("Target"),
                        "completed": fields.get("Completed"),
                        "cancelled": fields.get("Cancelled"),
                        "result": fields.get("Result"),
                    }
                )
        values.sort(key=lambda item: (item["due"] is None, item["due"] or "9999-12-31", item["state"], item["line"]))
        return values

    def current_markdown_paths(self) -> list[Path]:
        paths: list[Path] = []
        for relative in ("state", "people", "research/topics", "research/projects"):
            directory = self.root / relative
            if directory.is_dir():
                paths.extend(sorted(directory.rglob("*.md")))
        papers = self.root / "research/papers"
        if papers.is_dir():
            paths.extend(sorted(papers.glob("*/notes.md")))
        return paths

    def duplicate_lines(self) -> list[dict[str, Any]]:
        occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
        display: dict[str, str] = {}
        for path in self.current_markdown_paths():
            for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                stripped = raw.strip()
                if (
                    len(stripped) < 12
                    or stripped.startswith("#")
                    or stripped.startswith("- [")
                    or TODO_FIELD_RE.match(raw)
                    or FIELD_RE.match(stripped)
                    or LINK_ONLY_RE.match(stripped)
                ):
                    continue
                candidate = stripped.removeprefix("- ").strip()
                normalized = re.sub(r"\s+", " ", candidate).casefold()
                if len(normalized) < 12:
                    continue
                location = {
                    "path": path.relative_to(self.root).as_posix(),
                    "line": line_number,
                }
                occurrences[normalized].append(location)
                display.setdefault(normalized, candidate)
        groups: list[dict[str, Any]] = []
        for normalized, locations in occurrences.items():
            distinct_paths = {value["path"] for value in locations}
            if len(distinct_paths) < 2:
                continue
            groups.append({"text": display[normalized], "locations": locations})
        groups.sort(key=lambda item: (item["text"].casefold(), item["locations"]))
        return groups

    def people(self, query: str | None = None) -> list[dict[str, Any]]:
        directory = self.root / "people"
        values: list[dict[str, Any]] = []
        for path in sorted(directory.glob("*.md")) if directory.is_dir() else []:
            parsed = {
                match.group(1): match.group(2).strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if (match := FIELD_RE.match(line))
            }
            aliases = [value.strip() for value in parsed.get("Aliases", "").split(",") if value.strip() and value.strip() != "none"]
            values.append(
                {
                    "slug": path.stem,
                    "name": parsed.get("Name", ""),
                    "aliases": aliases,
                    "updated": parsed.get("Updated"),
                    "path": path.relative_to(self.root).as_posix(),
                }
            )
        if query is None:
            return values
        folded = query.casefold().strip()
        matches = [
            value
            for value in values
            if folded in {value["slug"].casefold(), value["name"].casefold(), *(alias.casefold() for alias in value["aliases"])}
        ]
        if not matches:
            raise ViewError("E_PERSON_NOT_FOUND", query)
        if len(matches) > 1:
            raise ViewError("E_PERSON_AMBIGUOUS", ",".join(value["slug"] for value in matches))
        return matches

    def research_papers(self, query: str | None = None) -> list[dict[str, Any]]:
        directory = self.root / "research/papers"
        values: list[dict[str, Any]] = []
        for metadata in sorted(directory.glob("*/metadata.md")) if directory.is_dir() else []:
            parsed = {
                match.group(1): match.group(2).strip()
                for line in metadata.read_text(encoding="utf-8").splitlines()
                if (match := FIELD_RE.match(line))
            }
            values.append(
                {
                    "slug": metadata.parent.name,
                    "title": parsed.get("Title", ""),
                    "authors": parsed.get("Authors", "unknown"),
                    "year": parsed.get("Year", "unknown"),
                    "sha256": parsed.get("SHA-256"),
                    "path": metadata.parent.relative_to(self.root).as_posix(),
                }
            )
        if query is None:
            return values
        folded = query.casefold().strip()
        matches = [
            value
            for value in values
            if folded == value["slug"].casefold()
            or folded in value["title"].casefold()
            or folded in value["authors"].casefold()
        ]
        if not matches:
            raise ViewError("E_RESEARCH_NOT_FOUND", query)
        return matches
