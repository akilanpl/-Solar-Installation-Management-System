"""Shared validated calendar commands."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class IntervalInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid_interval(self):
        if (
            self.starts_at.tzinfo is None
            or self.ends_at.tzinfo is None
            or self.ends_at <= self.starts_at
        ):
            raise ValueError("Use timezone-aware times with a positive interval.")
        if (self.ends_at - self.starts_at).total_seconds() > 86400:
            raise ValueError(
                "An appointment or leave interval must be at most one day; record longer leave by day."
            )
        return self


class AppointmentInput(IntervalInput):
    resource_type: Literal["survey", "installation"]
    resource_id: UUID
    technician_user_id: UUID
    override_reason: str | None = Field(default=None, min_length=5, max_length=1000)
