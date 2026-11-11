"""Dry-only Responses adapter; intentionally has no key, client, or execute path.

A future implementation must delegate the original ModelRequest plus validator to
DEVON's common call_model with one CallBudget per logical task. It must preserve
timeouts, attempts, byte/token bounds, structured output and error handling. This
stage does not implement or invoke that transport.
"""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .base import AdapterResult


class ResponsesAdapter:
    def __init__(self, *, dry_run: bool = True) -> None:
        if dry_run is not True:
            raise ValueError("stage1_offline_only")

    async def call(
        self,
        model: str,
        system_prompt: str,
        payload: dict[str, object],
        json_schema: dict[str, object],
    ) -> AdapterResult:
        if type(model) is not str or not model.strip():
            raise ValueError("adapter_envelope_invalid")
        if type(system_prompt) is not str or not system_prompt.strip():
            raise ValueError("adapter_envelope_invalid")
        if type(payload) is not dict or type(json_schema) is not dict:
            raise ValueError("adapter_envelope_invalid")
        try:
            Draft202012Validator.check_schema(json_schema)
            json.dumps(payload, allow_nan=False, ensure_ascii=False)
        except (SchemaError, TypeError, ValueError, RecursionError):
            raise ValueError("adapter_envelope_invalid") from None
        return AdapterResult(status="dry_run")
