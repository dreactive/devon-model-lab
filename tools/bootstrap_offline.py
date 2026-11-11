"""Build an isolated venv from already-installed distributions, without downloads.

Run with the system Python whose packages you want to use. Only files listed in
distribution metadata and located beneath its site-packages directory are copied.
This is an offline bootstrap, not a replacement for uv's reproducible resolver.
"""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys
import tomllib
import venv
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def bootstrap(root: Path) -> dict:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["name"] != "devon-model-lab":
        raise ValueError("not_model_lab")
    pending = [Requirement(value) for value in project["project"]["dependencies"]]
    resolved: dict[str, metadata.Distribution] = {}
    while pending:
        requirement = pending.pop()
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        name = canonicalize_name(requirement.name)
        distribution = metadata.distribution(requirement.name)
        if not requirement.specifier.contains(distribution.version, prereleases=True):
            raise ValueError("installed_version_outside_project_bounds")
        if name in resolved:
            continue
        if distribution.files is None:
            raise ValueError("distribution_has_no_file_manifest")
        resolved[name] = distribution
        pending.extend(Requirement(value) for value in distribution.requires or [])
    copies: list[tuple[Path, Path]] = []
    for _, distribution in sorted(resolved.items()):
        source_root = Path(distribution.locate_file("")).resolve()
        for entry in distribution.files or []:
            source = Path(distribution.locate_file(entry)).resolve()
            if not source.is_relative_to(source_root) or not source.is_file():
                continue
            relative = source.relative_to(source_root)
            if "__pycache__" not in relative.parts and source.suffix not in {".pyc", ".pyo"}:
                copies.append((source, relative))
    receipt = {
        "method": "copy_installed_distribution_files",
        "network_calls": 0,
        "system_site_packages": False,
        "python": sys.version.split()[0],
        "packages": {name: dist.version for name, dist in sorted(resolved.items())},
        "copied_files": len(copies),
        "limitations": [
            "Not a uv resolution or lockfile; versions come from this PC's installed distributions.",
            "No console-script entrypoints are installed; use python -m or the supplied .py scripts.",
        ],
    }
    requirements = (
        "# Offline bootstrap versions; regenerate a uv.lock during an authorized setup.\n"
        + "".join(f"{name}=={dist.version}\n" for name, dist in sorted(resolved.items()))
    )
    requirements_path = root / "requirements-offline.txt"
    receipt_path = root / "docs/offline-environment.json"
    # Existing receipts are evidence. Check consistency before modifying the venv.
    if requirements_path.exists() and requirements_path.read_text(encoding="utf-8") != requirements:
        raise ValueError("offline_requirements_changed")
    if receipt_path.exists() and json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
        raise ValueError("offline_receipt_changed")
    environment = root / ".venv"
    if environment.exists() and (environment / "Lib/site-packages").exists():
        existing = [p for p in (environment / "Lib/site-packages").iterdir()
                    if not p.name.startswith(("_virtualenv", ".gitignore"))]
        if existing:
            raise FileExistsError("venv_contains_packages")
    venv.EnvBuilder(with_pip=False, symlinks=False).create(environment)
    destination = environment / "Lib/site-packages"
    for source, relative in copies:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if not requirements_path.exists():
        with requirements_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(requirements)
    if not receipt_path.exists():
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    subprocess.run(
        [str(environment / "Scripts/python.exe"), "-B", "-c",
         "import httpx,pydantic,pydantic_settings,sqlalchemy,yaml,jsonschema; print('offline_dependencies_ok')"],
        check=True, cwd=root,
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = bootstrap(args.lab_root.resolve())
    except (OSError, ValueError, metadata.PackageNotFoundError, subprocess.CalledProcessError):
        parser.exit(1, "Offline bootstrap unavailable; check installed dependencies and use an empty local venv.\n")
    print(json.dumps({"packages": len(result["packages"]), "network_calls": 0, "model_calls": 0}))
