"""Validated descriptions of data-quality issues, without repair execution."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

NonnegativeRow = Annotated[StrictInt, Field(ge=0)]


class Issue(BaseModel):
    """A finding with caller-supplied evidence and a proposed recommendation.

    Affected rows are zero-based data-row indices. An empty list denotes an
    issue that is not tied to specific rows. Severity is supplied by the caller;
    this model does not determine it or authorize a repair.
    """

    model_config = ConfigDict(extra="forbid")

    issue_type: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence: list[str] = Field(min_length=1)
    affected_rows: list[NonnegativeRow]
    recommendation: str

    @field_validator("issue_type", "recommendation")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("evidence")
    @classmethod
    def nonblank_evidence(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("evidence entries must not be blank")
        return value

    @field_validator("affected_rows")
    @classmethod
    def distinct_rows(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("affected row indices must be distinct")
        return value
