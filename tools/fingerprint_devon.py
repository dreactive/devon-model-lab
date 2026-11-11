"""Read-only source fingerprint for before/after comparison; never load .env."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def snapshot(root: Path) -> dict:
    git_environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    paths = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True, check=True, env=git_environment,
    ).stdout.decode("utf-8").split("\0")
    files = {}
    for name in sorted(filter(None, paths)):
        # No key material is read even if a local checkout accidentally tracks it.
        if Path(name).name == ".env" or Path(name).name.startswith(".env."):
            continue
        path = root / name
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1"],
        capture_output=True, text=True, check=True, env=git_environment,
    ).stdout.splitlines()
    caches = []
    for directory, children, _ in os.walk(root):
        children[:] = [name for name in children if name not in {".git", ".venv", "node_modules"}]
        if "__pycache__" in children:
            caches.append(str((Path(directory) / "__pycache__").relative_to(root)))
    caches.sort()
    return {"tracked_files": files, "git_status": status, "bytecode_directories": caches}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devon-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.devon_root.resolve()):
        parser.exit(1, "Output inside the read-only DEVON checkout is rejected.\n")
    result = snapshot(args.devon_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"tracked_file_count": len(result["tracked_files"]), "model_calls": 0}))
