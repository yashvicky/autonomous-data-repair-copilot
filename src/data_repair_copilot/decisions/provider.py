"""Bounded provider decisions; never execute or authorize repairs."""

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DecisionRequest(BaseModel):
    """A question and the complete set of permitted selections."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    question: str
    choices: tuple[str, ...] = Field(min_length=2)

    @field_validator("request_id", "question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("choices")
    @classmethod
    def valid_choices(cls, choices: tuple[str, ...]) -> tuple[str, ...]:
        if any(not choice.strip() for choice in choices) or len(set(choices)) != len(choices):
            raise ValueError("choices must be nonblank and unique")
        return choices


class DecisionResult(BaseModel):
    """A provider recommendation, not an approval or a repair instruction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["selected", "needs_review"]
    choice: str | None = None
    confidence: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)] | None = None
    provider: str
    model_version: str | None = None
    review_reason: Literal["human_review", "provider_error", "invalid_response"] | None = None

    @field_validator("provider")
    @classmethod
    def valid_provider(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provider must not be blank")
        return value

    @field_validator("model_version")
    @classmethod
    def valid_version(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("model version must not be blank")
        return value

    @model_validator(mode="after")
    def valid_status(self) -> "DecisionResult":
        if self.status == "selected" and (self.choice is None or not self.choice.strip()):
            raise ValueError("selected decisions require a choice")
        if self.status == "selected" and self.review_reason is not None:
            raise ValueError("selected decisions cannot include a review reason")
        if self.status == "needs_review" and (
            self.choice is not None or self.confidence is not None
        ):
            raise ValueError("review decisions cannot select a choice or assign confidence")
        return self


class DecisionProvider(Protocol):
    """Interface for a future adapter; implementors must not execute repairs."""

    def decide(self, request: DecisionRequest) -> DecisionResult: ...


class HumanReviewProvider:
    """Defer every request to a human; no model or network is involved."""

    def decide(self, request: DecisionRequest) -> DecisionResult:
        return DecisionResult(
            status="needs_review", provider="human_review", review_reason="human_review"
        )


def request_decision(provider: DecisionProvider, request: DecisionRequest) -> DecisionResult:
    """Fail closed when a provider fails or returns an invalid or out-of-scope choice.

    Callers own review, provenance checks, and all repair authorization.
    Confidence is an uncalibrated provider value, never an approval threshold.
    """
    try:
        raw = provider.decide(request)
    except Exception:
        return DecisionResult(
            status="needs_review", provider="human_review", review_reason="provider_error"
        )
    try:
        if not isinstance(raw, DecisionResult):
            raise ValueError("provider must return a DecisionResult")
        result = DecisionResult.model_validate(raw.model_dump(), strict=True)
        if result.status == "selected" and result.choice not in request.choices:
            raise ValueError("choice is outside the request")
        return result
    except Exception:
        return DecisionResult(
            status="needs_review", provider="human_review", review_reason="invalid_response"
        )
