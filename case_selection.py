"""Strict lab-only case selections; source inputs and annotations stay in place."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable, TypeVar


class SelectionError(ValueError):
    """Only fixed failure codes leave the selection boundary."""


@dataclass(frozen=True)
class Selection:
    case_keys: frozenset[tuple[str, int]]
    model_ids: tuple[str, ...]
    fingerprint: dict[str, Any]
    selection_id: str

    def matches(self, case_id: str, version: int) -> bool:
        return type(case_id) is str and type(version) is int and (case_id, version) in self.case_keys


_ROOT_FIELDS = {"version", "selection_id", "reference_population", "split", "model_ids", "datasets", "review_status"}
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
T = TypeVar("T")


def _load(path: Path, code: str) -> tuple[Any, bytes]:
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SelectionError(code)
            result[key] = value
        return result

    def constant(_):
        raise SelectionError(code)

    try:
        raw = path.read_bytes()
        if len(raw) > 4 * 1024 * 1024:
            raise SelectionError(code)
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=object_pairs, parse_constant=constant)
        return value, raw
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        raise SelectionError(code) from None


def _identifier(value: Any, code: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise SelectionError(code)
    return value


def _key(row: Any, code: str) -> tuple[str, int]:
    if type(row) is not dict or set(row) != {"case_id", "version"}:
        raise SelectionError(code)
    identifier, version = _identifier(row["case_id"], code), row["version"]
    if type(version) is not int or version < 1:
        raise SelectionError(code)
    return identifier, version


def _dataset_path(lab: Path, relative: Any) -> Path:
    if (type(relative) is not str or "\\" in relative or not relative
            or any(part in {"", ".", ".."} for part in relative.split("/"))):
        raise SelectionError("selection_path_invalid")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or posix.parts[0] != "cases" or len(posix.parts) < 2 or posix.as_posix() != relative:
        raise SelectionError("selection_path_invalid")
    try:
        target = (lab / relative).resolve(strict=True)
        if not target.is_relative_to(lab / "cases") or not target.is_dir():
            raise SelectionError("selection_path_invalid")
        return target
    except (OSError, ValueError, RuntimeError):
        raise SelectionError("selection_path_invalid") from None


def _source(root: Path, identity: tuple[str, int], experiment: str) -> None:
    identifier, version = identity
    try:
        source_path = (root / "inputs" / f"{identifier}.v{version}.json").resolve(strict=True)
        if not source_path.is_relative_to(root / "inputs"):
            raise SelectionError("selection_source_invalid")
        envelope, _ = _load(source_path, "selection_source_invalid")
        if (type(envelope) is not dict or set(envelope) != {"case_id", "version", "control", "payload"}
                or type(envelope.get("case_id")) is not str or type(envelope.get("version")) is not int
                or (envelope["case_id"], envelope["version"]) != identity):
            raise SelectionError("selection_source_invalid")
        control = envelope["control"]
        expected_kind = "question" if experiment == "A" else "report"
        if (type(control) is not dict or control.get("split") != "dev"
                or control.get("kind") != expected_kind or control.get("synthetic") is not True
                or type(control.get("source_group_id")) is not str or not control["source_group_id"]):
            raise SelectionError("selection_source_invalid")
    except (OSError, KeyError, TypeError, ValueError, RuntimeError):
        raise SelectionError("selection_source_invalid") from None


def resolve_selection(selection_path: Path, *, lab_root: Path, cases_path: Path,
                      experiment: str, split: str) -> Selection:
    """Validate every selected source, then resolve the exact requested dataset."""
    try:
        lab = Path(lab_root).resolve(strict=True)
        folder = (lab / "selections").resolve(strict=True)
        path = Path(selection_path).resolve(strict=True)
        requested = Path(cases_path).resolve(strict=True)
        if (not folder.is_relative_to(lab) or not path.is_relative_to(folder)
                or not path.is_file() or not requested.is_relative_to(lab / "cases")):
            raise SelectionError("selection_path_invalid")
    except (OSError, RuntimeError, ValueError, TypeError):
        raise SelectionError("selection_path_invalid") from None
    value, raw = _load(path, "selection_document_invalid")
    if (type(value) is not dict or set(value) != _ROOT_FIELDS
            or type(value["version"]) is not int or value["version"] != 1
            or value["split"] != "dev" or value["review_status"] != "unreviewed"
            or value["reference_population"] != {"A": 35, "B": 17, "total": 52}):
        raise SelectionError("selection_document_invalid")
    if any(type(count) is not int for count in value["reference_population"].values()):
        raise SelectionError("selection_document_invalid")
    selection_id = _identifier(value["selection_id"], "selection_document_invalid")
    models = value["model_ids"]
    if (type(models) is not list or not models
            or any(type(model) is not str or not model.strip() or model != model.strip()
                   or any(character.isspace() or ord(character) < 32 for character in model) for model in models)
            or len(set(models)) != len(models)):
        raise SelectionError("selection_document_invalid")
    datasets = value["datasets"]
    if type(datasets) is not list or not datasets:
        raise SelectionError("selection_document_invalid")
    seen_roots, all_keys, selected = set(), set(), None
    for dataset in datasets:
        if (type(dataset) is not dict or set(dataset) != {"experiment", "cases_root", "cases"}
                or type(dataset["experiment"]) is not str or dataset["experiment"] not in {"A", "B"}
                or type(dataset["cases"]) is not list or not dataset["cases"]):
            raise SelectionError("selection_document_invalid")
        root = _dataset_path(lab, dataset["cases_root"])
        if root in seen_roots:
            raise SelectionError("selection_document_invalid")
        seen_roots.add(root)
        keys = []
        for row in dataset["cases"]:
            identity = _key(row, "selection_document_invalid")
            if identity in all_keys:
                raise SelectionError("selection_document_invalid")
            all_keys.add(identity)
            keys.append(identity)
        for identity in keys:
            _source(root, identity, dataset["experiment"])
        if root == requested and dataset["experiment"] == experiment:
            selected = frozenset(keys)
    if selected is None or type(experiment) is not str or experiment not in {"A", "B"} or split != "dev":
        raise SelectionError("selection_dataset_mismatch")
    return Selection(selected, tuple(models), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw)}, selection_id)


def filter_cases(cases: Iterable[T], selection: Selection) -> list[T]:
    """Return original loader objects only, refusing missing or duplicate identities."""
    selected, seen = [], set()
    try:
        for case in cases:
            if hasattr(case, "envelope"):
                envelope = case.envelope
                identity = envelope["case_id"], envelope["version"]
            else:
                identity = case.case_id, case.version
            if (type(identity[0]) is not str or type(identity[1]) is not int
                    or identity in seen):
                raise SelectionError("selection_cases_mismatch")
            seen.add(identity)
            if selection.matches(*identity):
                selected.append(case)
        if not selection.case_keys or seen & selection.case_keys != selection.case_keys:
            raise SelectionError("selection_cases_mismatch")
        return selected
    except (AttributeError, KeyError, TypeError, ValueError):
        raise SelectionError("selection_cases_mismatch") from None
