"""Locate the separate, read-only DEVON checkout before importing its code."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def attach_devon(devon_root: Path | None = None) -> Path:
    """Add only DEVON's Python source paths; never load dotenv or settings."""
    sys.dont_write_bytecode = True
    configured = devon_root if devon_root is not None else os.environ.get("DEVON_ROOT")
    root = Path(configured).expanduser().resolve() if configured else (
        Path(__file__).resolve().parent.parent / "devon"
    ).resolve()
    source_paths = (root / "ai/src", root / "ai/evals", root / "backend")
    required = (
        root / "ai/src/devon_ai/contracts.py",
        root / "ai/src/devon_ai/llm_tasks/report.py",
        root / "ai/src/devon_ai/llm_tasks/report_score.py",
        root / "backend/scripts/evaluation_output.py",
    )
    if not all(path.is_dir() for path in source_paths) or not all(
        path.is_file() for path in required
    ):
        raise ValueError("devon_root_invalid")
    for source in reversed(source_paths):
        value = str(source)
        if value not in sys.path:
            sys.path.insert(0, value)
    return root
