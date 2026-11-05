import pytest
from pydantic import ValidationError

from data_repair_copilot.decisions.provider import (
    DecisionProvider,
    DecisionRequest,
    DecisionResult,
    HumanReviewProvider,
    request_decision,
)


def sample_request() -> DecisionRequest:
    return DecisionRequest(request_id="case-1", question="Same entity?", choices=("yes", "no"))


def test_human_review_stub() -> None:
    provider: DecisionProvider = HumanReviewProvider()
    result = request_decision(provider, sample_request())
    assert result == DecisionResult(
        status="needs_review", provider="human_review", review_reason="human_review"
    )
    assert result.choice is None and result.confidence is None


def test_provider_contract() -> None:
    class FutureProvider:
        def decide(self, request: DecisionRequest) -> DecisionResult:
            assert request.choices == ("yes", "no")
            return DecisionResult(
                status="selected",
                choice="no",
                confidence=0.8,
                provider="synthetic",
                model_version="test-1",
            )

    provider: DecisionProvider = FutureProvider()
    result = request_decision(provider, sample_request())
    assert (result.status, result.choice, result.model_version) == ("selected", "no", "test-1")


def test_fail_closed() -> None:
    class BrokenProvider:
        def decide(self, request: DecisionRequest) -> DecisionResult:
            raise RuntimeError("provider unavailable")

    class BadChoiceProvider:
        def decide(self, request: DecisionRequest) -> DecisionResult:
            return DecisionResult(status="selected", choice="maybe", provider="test")

    class MalformedProvider:
        def decide(self, request: DecisionRequest) -> DecisionResult:
            return {"status": "selected", "choice": "yes"}  # type: ignore[return-value]

    class TamperedProvider:
        def decide(self, request: DecisionRequest) -> DecisionResult:
            return DecisionResult(status="selected", choice="yes", provider="test").model_copy(
                update={"confidence": 5}
            )

    for provider in (
        BrokenProvider(),
        BadChoiceProvider(),
        MalformedProvider(),
        TamperedProvider(),
    ):
        result = request_decision(provider, sample_request())
        assert result.status == "needs_review" and result.choice is None
        assert result.review_reason == (
            "provider_error" if isinstance(provider, BrokenProvider) else "invalid_response"
        )


def test_validation() -> None:
    for choices in [("yes", "yes"), ("yes", ""), ("yes",)]:
        with pytest.raises(ValidationError):
            DecisionRequest(request_id="1", question="question", choices=choices)
    for confidence in (-0.1, 1.1, float("nan"), float("inf"), True):
        with pytest.raises(ValidationError):
            DecisionResult(status="selected", choice="yes", provider="test", confidence=confidence)
    with pytest.raises(ValidationError):
        DecisionResult(status="needs_review", choice="yes", provider="test")
    with pytest.raises(ValidationError):
        DecisionResult(status="selected", provider="test")
