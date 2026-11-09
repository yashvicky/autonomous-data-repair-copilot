"""Separate caller-supplied evidence from unverified provider hypotheses."""

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    evidence_indices: tuple[StrictInt, ...] = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip() or len(value) > 2000:
            raise ValueError("hypothesis must be nonblank and at most 2000 characters")
        return value

    @field_validator("evidence_indices")
    @classmethod
    def unique_indices(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(i < 0 for i in value) or len(value) != len(set(value)):
            raise ValueError("evidence indices must be distinct and nonnegative")
        return value


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence: tuple[str, ...]
    hypotheses: tuple[Hypothesis, ...]
    status: str


class ExplanationProvider(Protocol):
    def explain(self, evidence: tuple[str, ...]) -> Sequence[Hypothesis]: ...


def explain_evidence(evidence: Sequence[str], provider: ExplanationProvider) -> Explanation:
    """Return supplied evidence unchanged; route invalid provider output to review.

    References show which observations were cited, not that a hypothesis is
    entailed or true. The caller must review all provider-generated text.
    """
    if isinstance(evidence, (str, bytes)) or not evidence or len(evidence) > 50:
        raise ValueError("provide 1 to 50 evidence strings")
    if any(not isinstance(item, str) or not item.strip() or len(item) > 2000 for item in evidence):
        raise ValueError("each evidence item must be nonblank and at most 2000 characters")
    facts = tuple(evidence)
    try:
        raw = provider.explain(facts)
        if not isinstance(raw, (list, tuple)) or not 1 <= len(raw) <= 10:
            raise ValueError("provider must return 1 to 10 hypotheses")
        hypotheses = []
        for item in raw:
            if not isinstance(item, Hypothesis):
                raise ValueError("invalid hypothesis")
            validated = Hypothesis.model_validate(item.model_dump(), strict=True)
            if any(index >= len(facts) for index in validated.evidence_indices):
                raise ValueError("unknown evidence reference")
            hypotheses.append(validated)
        return Explanation(evidence=facts, hypotheses=tuple(hypotheses), status="review_required")
    except Exception:
        return Explanation(evidence=facts, hypotheses=(), status="provider_unavailable")
