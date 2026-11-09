import pytest

from data_repair_copilot.explanations.provider import Hypothesis, explain_evidence


def test_separate_evidence_and_hypotheses() -> None:
    class SyntheticProvider:
        def explain(self, evidence):
            assert evidence == ("5 values missing", "Other rows are populated")
            return [Hypothesis(text="A source field may be missing.", evidence_indices=(0,))]

    evidence = ["5 values missing", "Other rows are populated"]
    result = explain_evidence(evidence, SyntheticProvider())
    assert result.evidence == tuple(evidence)
    assert result.hypotheses[0].evidence_indices == (0,)
    assert result.hypotheses[0].text == "A source field may be missing."
    assert result.status == "review_required"
    assert evidence == ["5 values missing", "Other rows are populated"]


def test_fail_closed() -> None:
    class Broken:
        def explain(self, evidence):
            raise RuntimeError("private provider details")

    class Unsupported:
        def explain(self, evidence):
            return [Hypothesis(text="Claim", evidence_indices=(1,))]

    class Malformed:
        def explain(self, evidence):
            return [
                Hypothesis(text="Claim", evidence_indices=(0,)).model_copy(
                    update={"evidence_indices": (True,)}
                )
            ]

    for provider in (Broken(), Unsupported(), Malformed()):
        result = explain_evidence(["Observed"], provider)
        assert result.status == "provider_unavailable"
        assert result.evidence == ("Observed",) and result.hypotheses == ()
        assert "private provider details" not in repr(result)


def test_input_validation() -> None:
    class NeverCall:
        def explain(self, evidence):
            raise AssertionError("should not be invoked")

    for evidence in ([], "text", [""], ["x" * 2001], ["x"] * 51, [1]):
        with pytest.raises(ValueError):
            explain_evidence(evidence, NeverCall())


def test_grok_adapter_with_simulated_transport() -> None:
    import json

    from data_repair_copilot.explanations.grok import GrokExplanationProvider

    requests = []

    def transport(request):
        requests.append(request)
        return {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(
                                {
                                    "hypotheses": [
                                        {
                                            "text": "A source field may be missing.",
                                            "evidence_indices": [0],
                                        }
                                    ]
                                }
                            ),
                        }
                    ],
                }
            ],
        }

    result = explain_evidence(
        ["5 values missing"], GrokExplanationProvider(model="grok-test", transport=transport)
    )
    assert result.status == "review_required"
    assert result.evidence == ("5 values missing",)
    assert result.hypotheses[0].evidence_indices == (0,)
    assert requests[0]["store"] is False
    assert requests[0]["model"] == "grok-test"
    assert json.loads(requests[0]["input"][1]["content"]) == {"evidence": ["5 values missing"]}
    assert "tools" not in requests[0]
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    unavailable = GrokExplanationProvider(
        model="grok-test", transport=lambda request: {"status": "incomplete"}
    )
    assert explain_evidence(["Observed"], unavailable).status == "provider_unavailable"
