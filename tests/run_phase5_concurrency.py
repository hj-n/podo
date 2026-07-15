#!/usr/bin/env python3
"""Exercise strict three-way State merge and overlapping conflict safety."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "product/.podo/scripts"))
from context_store import ContextStore  # noqa: E402
from transaction_store import TransactionError, TransactionManager  # noqa: E402
from run_phase5_transactions import apply, build, capture  # noqa: E402


def request(workspace: Path, name: str, state_text: str) -> Path:
    state = workspace / "state/synthetic-planning.md"
    value = {
        "event": {"title": f"Concurrency {name}", "context": "Phase 5 concurrency fixture다."},
        "updates": [
            {
                "state_slug": "synthetic-planning",
                "expected_state_sha256": hashlib.sha256(state.read_bytes()).hexdigest(),
                "delta_title": f"Concurrency {name}",
                "changed": f"- {name}",
                "why": "사용자가 합성 fixture에서 명확히 결정했다.",
                "confidence": "confirmed",
                "needs_confirmation": "- 없음",
                "state_markdown": state_text,
            }
        ],
    }
    path = workspace / f".podo-work/requests/{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def transaction_id(workspace: Path) -> str:
    values = sorted((workspace / ".podo-work/transactions").glob("context-*"))
    if len(values) != 1:
        raise AssertionError(f"expected one transaction: {values}")
    return values[0].name


def resume(workspace: Path, value: str) -> dict:
    store = ContextStore(workspace)
    return TransactionManager(workspace).commit(
        value,
        store.validate_workspace,
        lambda text, slug: store.validate_state_text(text, slug, requires_delta_token=False),
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase5-concurrency-") as temporary:
        root = Path(temporary)

        workspace = root / "non-overlap"
        build(workspace)
        state_path = workspace / "state/synthetic-planning.md"
        base = state_path.read_text(encoding="utf-8")
        decision = base.replace(
            "\n## TODO\n",
            "\n- NONOVERLAP_DECISION ([Delta]({{DELTA_LINK}}))\n\n## TODO\n",
        )
        todo = base.replace(
            "\n## Reasons\n",
            "\n- [ ] NONOVERLAP_TODO\n  - Created: 2026-07-15\n  - Evidence: [Delta]({{DELTA_LINK}})\n\n## Reasons\n",
        )
        first_capture = capture(workspace, root, "nonoverlap-first")
        first_request = request(workspace, "nonoverlap-first", decision)
        prepared = apply(workspace, first_capture, first_request, "after-prepared")
        if prepared.returncode == 0 or "E_INJECTED_FAILURE" not in prepared.stderr:
            raise AssertionError(prepared.stdout + prepared.stderr)
        first_transaction = transaction_id(workspace)

        second_capture = capture(workspace, root, "nonoverlap-second")
        second_request = request(workspace, "nonoverlap-second", todo)
        second = apply(workspace, second_capture, second_request)
        if second.returncode:
            raise AssertionError(second.stdout + second.stderr)
        result = resume(workspace, first_transaction)
        if result.get("status") != "committed":
            raise AssertionError(str(result))
        merged = state_path.read_text(encoding="utf-8")
        if "NONOVERLAP_DECISION" not in merged or "NONOVERLAP_TODO" not in merged:
            raise AssertionError(merged)
        if list((workspace / ".podo-work/transactions").glob("*")):
            raise AssertionError("merged transaction was not finalized")
        print("PASS non-overlapping concurrent State changes merge and validate")

        workspace = root / "overlap"
        build(workspace)
        state_path = workspace / "state/synthetic-planning.md"
        base = state_path.read_text(encoding="utf-8")
        old = "- 합성 프로젝트 회의는 금요일 오전 9시에 한다."
        first_text = base.replace(old, "- CONFLICT_A ([Delta]({{DELTA_LINK}}))")
        second_text = base.replace(old, "- CONFLICT_B ([Delta]({{DELTA_LINK}}))")
        first_capture = capture(workspace, root, "conflict-first")
        first_request = request(workspace, "conflict-first", first_text)
        prepared = apply(workspace, first_capture, first_request, "after-prepared")
        if prepared.returncode == 0:
            raise AssertionError(prepared.stdout + prepared.stderr)
        first_transaction = transaction_id(workspace)
        second_capture = capture(workspace, root, "conflict-second")
        second_request = request(workspace, "conflict-second", second_text)
        second = apply(workspace, second_capture, second_request)
        if second.returncode:
            raise AssertionError(second.stdout + second.stderr)
        before_resume = state_path.read_bytes()
        try:
            resume(workspace, first_transaction)
        except TransactionError as error:
            if error.code != "E_STATE_CONFLICT":
                raise
        else:
            raise AssertionError("overlapping State changes unexpectedly merged")
        if state_path.read_bytes() != before_resume or "CONFLICT_B" not in state_path.read_text(encoding="utf-8"):
            raise AssertionError("conflict changed the current State")
        journal = json.loads(
            (workspace / f".podo-work/transactions/{first_transaction}/journal.json").read_text(encoding="utf-8")
        )
        if journal.get("failure", {}).get("code") != "E_STATE_CONFLICT":
            raise AssertionError(str(journal))
        print("PASS overlapping concurrent State changes preserve current State and require recovery")


if __name__ == "__main__":
    main()
