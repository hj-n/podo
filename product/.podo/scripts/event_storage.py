#!/usr/bin/env python3
"""Lossless content-addressed storage for immutable Event originals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHUNK_SIZE = 256 * 1024
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.+)$", re.MULTILINE)
PLAN_RE = re.compile(r"^event-storage-[a-f0-9]{20}$")


class EventStorageError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def fail(code: str, detail: str) -> None:
    raise EventStorageError(code, detail)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def fields(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in FIELD_RE.finditer(text)}


def replace_field(text: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)}:\s*.+$", re.MULTILINE)
    if not pattern.search(text):
        fail("E_EVENT_METADATA", f"missing field: {name}")
    return pattern.sub(f"{name}: {value}", text, count=1)


class EventStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.events = self.root / "events"
        self.objects = self.events / ".objects/sha256"
        self.plans = self.root / ".podo-work/event-storage-plans"
        self.backups = self.root / ".podo-backups"

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            fail("E_EVENT_STORAGE_PATH", str(path))

    def safe_path(self, value: str) -> Path:
        if not value or value.startswith("/") or ".." in Path(value).parts:
            fail("E_EVENT_STORAGE_PATH", value)
        path = (self.root / value).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            fail("E_EVENT_STORAGE_PATH", value)
        return path

    def chunks(self, raw: bytes) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for offset in range(0, len(raw), CHUNK_SIZE):
            value = raw[offset : offset + CHUNK_SIZE]
            values.append({"sha256": digest(value), "size": len(value)})
        if not values:
            values.append({"sha256": digest(b""), "size": 0})
        return values

    def object_path(self, sha256: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", sha256):
            fail("E_EVENT_OBJECT_HASH", sha256)
        return self.objects / sha256[:2] / sha256[2:]

    def read_original(self, metadata: Path) -> tuple[Path, bytes, str]:
        text = metadata.read_text(encoding="utf-8")
        value = fields(text).get("Original-Entrypoint")
        if not value:
            fail("E_EVENT_METADATA", f"{self.relative(metadata)} has no Original-Entrypoint")
        entrypoint = (metadata.parent / value).resolve()
        try:
            entrypoint.relative_to(self.root)
        except ValueError:
            fail("E_EVENT_STORAGE_PATH", value)
        if entrypoint.name == "manifest.json":
            return entrypoint, self.materialize_manifest(entrypoint), text
        if entrypoint.is_symlink() or not entrypoint.is_file():
            fail("E_EVENT_ORIGINAL", self.relative(metadata))
        return entrypoint, entrypoint.read_bytes(), text

    def materialize_manifest(self, manifest_path: Path) -> bytes:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            fail("E_EVENT_MANIFEST", str(error))
        if not isinstance(manifest, dict) or manifest.get("format") != "podo-chunked-original-v1":
            fail("E_EVENT_MANIFEST", "unsupported manifest")
        parts: list[bytes] = []
        for chunk in manifest.get("chunks", []):
            if not isinstance(chunk, dict):
                fail("E_EVENT_MANIFEST", "chunk entry must be an object")
            path = self.object_path(str(chunk.get("sha256") or ""))
            if path.is_symlink() or not path.is_file():
                fail("E_EVENT_OBJECT_MISSING", self.relative(path))
            raw = path.read_bytes()
            if len(raw) != chunk.get("size") or digest(raw) != chunk.get("sha256"):
                fail("E_EVENT_OBJECT_HASH", self.relative(path))
            parts.append(raw)
        raw = b"".join(parts)
        if len(raw) != manifest.get("size") or digest(raw) != manifest.get("sha256"):
            fail("E_EVENT_MANIFEST_HASH", self.relative(manifest_path))
        return raw

    def candidate_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for metadata in sorted(self.events.glob("*/*/*/metadata.md")):
            entrypoint, raw, text = self.read_original(metadata)
            if entrypoint.name == "manifest.json":
                continue
            try:
                entrypoint.relative_to((metadata.parent / "original").resolve())
            except ValueError:
                continue
            records.append(
                {
                    "metadata": self.relative(metadata),
                    "original": self.relative(entrypoint),
                    "sha256": digest(raw),
                    "size": len(raw),
                    "metadata_sha256": digest(text.encode("utf-8")),
                    "chunks": self.chunks(raw),
                }
            )
        return records

    def save_plan(self, material: dict[str, Any]) -> dict[str, Any]:
        identity = digest(json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8"))[:20]
        plan_id = f"event-storage-{identity}"
        plan = {
            "plan_version": 1,
            "plan_id": plan_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **material,
        }
        path = self.plans / f"{plan_id}.json"
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            return existing
        atomic_json(path, plan)
        return plan

    def plan_dedup(self) -> dict[str, Any]:
        records = self.candidate_records()
        seen: set[str] = set()
        unique_bytes = 0
        total_bytes = sum(record["size"] for record in records)
        for record in records:
            for chunk in record["chunks"]:
                if chunk["sha256"] not in seen:
                    seen.add(chunk["sha256"])
                    unique_bytes += chunk["size"]
        backup_id = "event-storage-" + digest(json.dumps(records, sort_keys=True).encode("utf-8"))[:16]
        return self.save_plan(
            {
                "kind": "deduplicate",
                "status": "planned",
                "backup_id": backup_id,
                "records": records,
                "summary": {
                    "event_count": len(records),
                    "source_bytes": total_bytes,
                    "unique_chunk_bytes": unique_bytes,
                    "potential_event_bytes_saved": total_bytes - unique_bytes,
                    "legacy_originals_preserved_in_backup": True,
                },
            }
        )

    def plan_rollback(self, backup_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"event-storage-[a-f0-9]{16}", backup_id):
            fail("E_EVENT_STORAGE_BACKUP", backup_id)
        backup = self.backups / backup_id
        manifest_path = backup / "backup.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            fail("E_EVENT_STORAGE_BACKUP", str(error))
        if manifest.get("backup_id") != backup_id or manifest.get("kind") != "event-storage-dedup":
            fail("E_EVENT_STORAGE_BACKUP", "backup identity mismatch")
        records: list[dict[str, Any]] = []
        for source in manifest.get("records", []):
            metadata = self.safe_path(str(source["metadata"]))
            original = self.safe_path(str(source["original"]))
            manifest_current = metadata.parent / "original/manifest.json"
            if not metadata.is_file() or not manifest_current.is_file() or original.exists():
                fail("E_EVENT_STORAGE_ROLLBACK_STALE", str(source["metadata"]))
            backup_metadata = backup / "user-data" / source["metadata"]
            backup_original = backup / "user-data" / source["original"]
            if not backup_metadata.is_file() or not backup_original.is_file():
                fail("E_EVENT_STORAGE_BACKUP", str(source["metadata"]))
            if digest(backup_original.read_bytes()) != source["sha256"]:
                fail("E_EVENT_STORAGE_BACKUP", str(source["original"]))
            records.append(
                {
                    **source,
                    "current_metadata_sha256": digest(metadata.read_bytes()),
                    "current_manifest_sha256": digest(manifest_current.read_bytes()),
                }
            )
        return self.save_plan(
            {
                "kind": "rollback",
                "status": "planned",
                "backup_id": backup_id,
                "records": records,
                "summary": {"event_count": len(records), "restores_legacy_originals": True},
            }
        )

    def load_plan(self, plan_id: str) -> tuple[Path, dict[str, Any]]:
        if not PLAN_RE.fullmatch(plan_id):
            fail("E_EVENT_STORAGE_PLAN", plan_id)
        path = self.plans / f"{plan_id}.json"
        if path.is_symlink() or not path.is_file():
            fail("E_EVENT_STORAGE_PLAN", plan_id)
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("plan_id") != plan_id:
            fail("E_EVENT_STORAGE_PLAN", "identity mismatch")
        return path, value

    def verify_record(self, record: dict[str, Any]) -> tuple[Path, Path, bytes, str]:
        metadata = self.safe_path(str(record["metadata"]))
        original = self.safe_path(str(record["original"]))
        if metadata.is_symlink() or original.is_symlink() or not metadata.is_file() or not original.is_file():
            fail("E_EVENT_STORAGE_PLAN_STALE", str(record["metadata"]))
        metadata_text = metadata.read_text(encoding="utf-8")
        raw = original.read_bytes()
        if digest(metadata_text.encode("utf-8")) != record["metadata_sha256"] or digest(raw) != record["sha256"]:
            fail("E_EVENT_STORAGE_PLAN_STALE", str(record["metadata"]))
        return metadata, original, raw, metadata_text

    def apply(self, plan_id: str) -> dict[str, Any]:
        plan_path, plan = self.load_plan(plan_id)
        if plan.get("status") == "applied":
            return {"status": "already-applied", "plan_id": plan_id, "backup_id": plan.get("backup_id")}
        if plan.get("status") != "planned":
            fail("E_EVENT_STORAGE_PLAN", "plan is not applicable")
        if plan.get("kind") == "rollback":
            return self.apply_rollback(plan_path, plan)
        if plan.get("kind") != "deduplicate":
            fail("E_EVENT_STORAGE_PLAN", "unknown plan kind")
        verified = [self.verify_record(record) for record in plan["records"]]
        backup = self.backups / str(plan["backup_id"])
        if backup.exists() or backup.is_symlink():
            fail("E_EVENT_STORAGE_BACKUP", self.relative(backup))
        backup.mkdir(parents=True)
        applied: list[tuple[Path, Path, Path]] = []
        try:
            for record, (metadata, original, raw, metadata_text) in zip(plan["records"], verified, strict=True):
                metadata_backup = backup / "user-data" / record["metadata"]
                original_backup = backup / "user-data" / record["original"]
                metadata_backup.parent.mkdir(parents=True, exist_ok=True)
                original_backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(metadata, metadata_backup)
                shutil.copy2(original, original_backup)
                chunks = self.chunks(raw)
                for index, chunk in enumerate(chunks):
                    value = raw[index * CHUNK_SIZE : (index + 1) * CHUNK_SIZE]
                    object_path = self.object_path(chunk["sha256"])
                    if object_path.is_file():
                        if digest(object_path.read_bytes()) != chunk["sha256"]:
                            fail("E_EVENT_OBJECT_HASH", self.relative(object_path))
                    else:
                        atomic_write(object_path, value)
                manifest = {
                    "format": "podo-chunked-original-v1",
                    "sha256": record["sha256"],
                    "size": record["size"],
                    "chunk_size": CHUNK_SIZE,
                    "chunks": chunks,
                    "legacy_filename": original.name,
                }
                manifest_path = metadata.parent / "original/manifest.json"
                atomic_json(manifest_path, manifest)
                if self.materialize_manifest(manifest_path) != raw:
                    fail("E_EVENT_MANIFEST_HASH", record["metadata"])
                new_metadata = replace_field(metadata_text, "Original-Entrypoint", "./original/manifest.json")
                atomic_write(metadata, new_metadata.encode("utf-8"))
                original.unlink()
                applied.append((metadata, original, manifest_path))
                if os.environ.get("PODO_TEST_EVENT_STORAGE_FAIL_AT") == str(len(applied)):
                    fail("E_EVENT_STORAGE_INJECTED", str(len(applied)))
            backup_manifest = {
                "backup_version": 1,
                "kind": "event-storage-dedup",
                "backup_id": plan["backup_id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "plan_id": plan_id,
                "records": plan["records"],
            }
            atomic_json(backup / "backup.json", backup_manifest)
            plan["status"] = "applied"
            plan["applied_at"] = datetime.now(timezone.utc).isoformat()
            atomic_json(plan_path, plan)
            return {"status": "applied", "plan_id": plan_id, "backup_id": plan["backup_id"], "summary": plan["summary"]}
        except Exception:
            for metadata, original, manifest_path in reversed(applied):
                relative_metadata = self.relative(metadata)
                relative_original = self.relative(original)
                shutil.copy2(backup / "user-data" / relative_metadata, metadata)
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup / "user-data" / relative_original, original)
                manifest_path.unlink(missing_ok=True)
            shutil.rmtree(backup, ignore_errors=True)
            raise

    def apply_rollback(self, plan_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
        backup = self.backups / str(plan["backup_id"])
        verified: list[tuple[dict[str, Any], Path, Path, Path]] = []
        for record in plan["records"]:
            metadata = self.safe_path(str(record["metadata"]))
            original = self.safe_path(str(record["original"]))
            manifest = metadata.parent / "original/manifest.json"
            if (
                not metadata.is_file()
                or not manifest.is_file()
                or original.exists()
                or digest(metadata.read_bytes()) != record["current_metadata_sha256"]
                or digest(manifest.read_bytes()) != record["current_manifest_sha256"]
            ):
                fail("E_EVENT_STORAGE_ROLLBACK_STALE", str(record["metadata"]))
            verified.append((record, metadata, original, manifest))
        for record, metadata, original, manifest in verified:
            backup_metadata = backup / "user-data" / record["metadata"]
            backup_original = backup / "user-data" / record["original"]
            original.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(original, backup_original.read_bytes())
            atomic_write(metadata, backup_metadata.read_bytes())
            manifest.unlink()
        plan["status"] = "applied"
        plan["applied_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(plan_path, plan)
        return {
            "status": "applied",
            "kind": "rollback",
            "plan_id": plan["plan_id"],
            "backup_id": plan["backup_id"],
            "summary": plan["summary"],
        }

    def materialize_event(self, metadata_value: str) -> dict[str, Any]:
        metadata = self.safe_path(metadata_value)
        _, raw, _ = self.read_original(metadata)
        return {"metadata": metadata_value, "sha256": digest(raw), "size": len(raw), "bytes": raw}
