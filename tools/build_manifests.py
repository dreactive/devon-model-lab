"""Generate local service manifests without importing or changing DEVON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


def build(devon_root: Path, lab_root: Path) -> list[Path]:
    source = devon_root / "ai/evals/service_regression/runtime-manifest.json"
    raw = json.loads(source.read_text(encoding="utf-8-sig"))
    config = yaml.safe_load((lab_root / "models.yaml").read_text(encoding="utf-8"))
    models = config["models"]
    names = [item["name"] for item in models]
    if len(names) != len(set(names)):
        raise ValueError("duplicate_model_name")
    planned: list[tuple[Path, dict]] = []
    for model in models:
        if not model.get("enabled", False):
            continue
        name, model_id = model["name"], model.get("model_id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
            raise ValueError("invalid_model_name")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("enabled_model_needs_id")
        manifest = {
            "prompts": [
                {
                    **entry,
                    "model": model_id,
                    "template_path": str((source.parent / entry["template_path"]).resolve()),
                }
                for entry in raw["prompts"]
            ],
            "limits": raw["limits"],
        }
        if "task_limits" in raw:
            manifest["task_limits"] = raw["task_limits"]
        target = lab_root / "manifests" / f"{name}.json"
        # Validate every output name before creating any file; refuse overwrite.
        if target.exists():
            raise FileExistsError("manifest_already_exists")
        planned.append((target, manifest))
    for target, manifest in planned:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    return [target for target, _ in planned]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--devon-root", type=Path, required=True)
    parser.add_argument("--lab-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        created = build(args.devon_root.resolve(), args.lab_root.resolve())
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        parser.exit(1, "Manifest generation rejected; check configuration and existing output names.\n")
    print(json.dumps({"created": [path.name for path in created], "model_calls": 0}))
