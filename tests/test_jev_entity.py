import io
import json
from unittest.mock import patch
from urllib.request import HTTPRedirectHandler

import pytest

from data_repair_copilot.decisions.jev_entity import match_entities, typesafe_http_transport

MODEL = "jev-1.14.0"
LEFT = {"name": "Ada Example", "zip": "00123"}
RIGHT = {"name": "A. Example", "zip": "00123"}


def response(choice="same_entity"):
    probabilities = {key: 0.0 for key in ("same_entity", "different_entity", "needs_review")}
    probabilities[choice] = 1.0
    return {
        "model": MODEL,
        "answers": {
            "entity_match": {
                "type": "choice",
                "choice": choice,
                "confidence": 0.9,
                "probabilities": probabilities,
            }
        },
    }


def test_request_and_decisions() -> None:
    payloads = []
    for choice in ("same_entity", "different_entity", "needs_review"):

        def transport(payload, selected=choice):
            payloads.append(payload)
            return response(selected)

        result = match_entities(LEFT, RIGHT, model=MODEL, transport=transport)
        assert (result.outcome, result.confidence, result.model_version, result.reason) == (
            choice,
            0.9,
            MODEL,
            "model_decision",
        )
    assert payloads[0]["state"] == {"left": LEFT, "right": RIGHT}
    assert payloads[0]["model"] == MODEL
    question = payloads[0]["questions"]["entity_match"]
    assert question["type"] == "choice"
    assert set(question["criteria"]) == {"same_entity", "different_entity", "needs_review"}


def test_fail_closed() -> None:
    def broken(payload):
        raise RuntimeError("secret sensitive provider error")

    result = match_entities(LEFT, RIGHT, model=MODEL, transport=broken)
    assert (result.outcome, result.confidence, result.reason) == (
        "needs_review",
        None,
        "provider_error",
    )
    assert "secret" not in repr(result)
    invalid = [
        None,
        {},
        {"model": "jev-latest", "answers": response()["answers"]},
        response() | {"answers": {"entity_match": {"type": "choice", "choice": "maybe"}}},
    ]
    bad_confidence = response()
    bad_confidence["answers"]["entity_match"]["confidence"] = float("nan")
    invalid.append(bad_confidence)
    bad_probabilities = response()
    bad_probabilities["answers"]["entity_match"]["probabilities"]["same_entity"] = 0.3
    invalid.append(bad_probabilities)
    for bad in invalid:
        result = match_entities(LEFT, RIGHT, model=MODEL, transport=lambda payload, item=bad: item)
        assert (result.outcome, result.confidence, result.reason) == (
            "needs_review",
            None,
            "invalid_response",
        )


def test_input_validation() -> None:
    calls = []

    def transport(payload):
        calls.append(payload)
        return response()

    for model in ("jev-preview", "jev-latest", "", "jev-1.14.0\n"):
        with pytest.raises(ValueError):
            match_entities(LEFT, RIGHT, model=model, transport=transport)
    for bad in ({}, {"name": 3}, {"": "x"}, {"x": "a" * 70000}):
        with pytest.raises(ValueError):
            match_entities(bad, RIGHT, model=MODEL, transport=transport)
    assert calls == []
    for key in ("", "key\nother"):
        with pytest.raises(ValueError):
            typesafe_http_transport(key)


def test_http_transport() -> None:
    class FakeOpener:
        def open(self, request, timeout):
            assert request.full_url == "https://api.typesafe.ai/v1/systemone"
            assert request.get_method() == "POST"
            assert request.get_header("Authorization") == "Bearer synthetic-key"
            assert timeout == 2
            assert json.loads(request.data) == {"model": MODEL}
            return io.BytesIO(json.dumps(response()).encode())

    with patch(
        "data_repair_copilot.decisions.jev_entity.build_opener", return_value=FakeOpener()
    ) as factory:
        transport = typesafe_http_transport("synthetic-key", timeout_seconds=2)
        assert transport({"model": MODEL}) == response()
        assert any(isinstance(x, HTTPRedirectHandler) for x in factory.call_args.args)
        handler = next(x for x in factory.call_args.args if isinstance(x, HTTPRedirectHandler))
        assert handler.redirect_request(None, None, 302, None, None, "https://other.test") is None
