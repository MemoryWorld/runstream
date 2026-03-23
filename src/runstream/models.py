from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RunRecord(BaseModel):
    run_id: str = Field(min_length=1)
    project: str = Field(min_length=1)
    started_at: datetime
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    config_ref: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def status_ok(cls, v: str) -> str:
        allowed = {"pending", "running", "completed", "failed", "cancelled"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

    def canonical_json_bytes(self) -> bytes:
        """Stable JSON for content hashing (sorted keys)."""
        payload = self.model_dump(mode="json")
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
