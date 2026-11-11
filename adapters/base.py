"""Provider-neutral experiment interface; no transport implementation lives here."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AdapterResult:
    status: str
    model_calls: int = 0
    data: None = None


class ModelAdapter(Protocol):
    async def call(
        self,
        model: str,
        system_prompt: str,
        payload: dict[str, object],
        json_schema: dict[str, object],
    ) -> AdapterResult:
        """Validate an offline envelope and return an explicit dry-run sentinel."""
        ...
