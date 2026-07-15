#!/usr/bin/env python3
"""Run generated install.sh against disposable HTTP Release assets."""

from __future__ import annotations

import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_release.py"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args) -> None:
        pass


def run(args: list[str], **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, **kwargs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="podo-phase6-bootstrap-") as temporary:
        base = Path(temporary)
        current_version = (ROOT / "product/.podo/VERSION").read_text(encoding="utf-8").strip()
        assets = base / f"server/releases/download/v{current_version}"
        built = run([sys.executable, str(BUILDER), "--output", str(assets)], cwd=ROOT)
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        metadata = json.loads((assets / "release.json").read_text(encoding="utf-8"))

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(base / "server"), **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            release_base = f"http://127.0.0.1:{server.server_port}/releases/download/v{current_version}"
            env = os.environ.copy()
            env.update({"PODO_TEST_RELEASES": "1", "PODO_RELEASE_BASE": release_base})
            workspace = base / "workspace with space"
            installed = run(["sh", str(assets / "install.sh"), str(workspace)], cwd=base, env=env)
            if installed.returncode or "INSTALLED" not in installed.stdout:
                raise AssertionError(installed.stdout + installed.stderr)
            manifest = json.loads((workspace / ".podo/install-manifest.json").read_text(encoding="utf-8"))
            if manifest["product_version"] != current_version or manifest["source"]["archive_sha256"] != metadata["archive_sha256"]:
                raise AssertionError(str(manifest))
            print("PASS generated bootstrap installs a checksummed package into a quoted path")

            damaged = base / "damaged-server"
            shutil.copytree(assets, damaged)
            (damaged / metadata["checksum_asset"]).write_text(
                "f" * 64 + f"  {metadata['archive_asset']}\n", encoding="utf-8"
            )
            damaged_handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(damaged), **kwargs)
            damaged_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), damaged_handler)
            damaged_thread = threading.Thread(target=damaged_server.serve_forever, daemon=True)
            damaged_thread.start()
            try:
                damaged_env = os.environ.copy()
                damaged_env.update(
                    {
                        "PODO_TEST_RELEASES": "1",
                        "PODO_RELEASE_BASE": f"http://127.0.0.1:{damaged_server.server_port}",
                    }
                )
                rejected_workspace = base / "checksum-rejected"
                rejected = run(
                    ["sh", str(damaged / "install.sh"), str(rejected_workspace)],
                    cwd=base,
                    env=damaged_env,
                )
                if rejected.returncode == 0 or "E_CHECKSUM_MISMATCH" not in rejected.stderr:
                    raise AssertionError(rejected.stdout + rejected.stderr)
                if rejected_workspace.exists():
                    raise AssertionError("checksum failure created a Workspace")
            finally:
                damaged_server.shutdown()
                damaged_server.server_close()
                damaged_thread.join()
            print("PASS bootstrap checksum failure occurs before Workspace creation")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    main()
