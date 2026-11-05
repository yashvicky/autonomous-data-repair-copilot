"""Explicit Jev entity-match adapter. A returned decision never authorizes a repair."""

import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

Outcome = Literal["same_entity", "different_entity", "needs_review"]
Transport = Callable[[dict], dict]
_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
_CHOICES = {"same_entity", "different_entity", "needs_review"}
_MODEL = re.compile(r"jev-\d+\.\d+\.\d+\Z")
_MAX_BYTES = 65536


@dataclass(frozen=True)
class EntityMatchResult:
    outcome: Outcome
    confidence: float | None
    model_version: str | None
    reason: Literal["model_decision", "provider_error", "invalid_response"]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def typesafe_http_transport(api_key: str, *, timeout_seconds: float = 10.0) -> Transport:
    """Build an explicit HTTP transport; construction does not perform a call.

    The caller is responsible for authorizing spending and any data sent.
    The fixed HTTPS endpoint does not follow redirects or use environment proxies.
    No retries occur. Never log credentials, request data, or raw errors.
    """
    if not isinstance(api_key, str) or not api_key.strip() or "\n" in api_key or "\r" in api_key:
        raise ValueError("api_key must be a nonblank single-line string")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("timeout must be a positive finite number")

    def send(payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(body) > _MAX_BYTES:
            raise ValueError("request too large")
        request = Request(
            _ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        with opener.open(request, timeout=timeout_seconds) as response:
            raw = response.read(_MAX_BYTES + 1)
        if len(raw) > _MAX_BYTES:
            raise ValueError("response too large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("response must be an object")
        return result

    return send


def _valid_record(record: Mapping[str, str | None]) -> bool:
    return (
        isinstance(record, Mapping)
        and bool(record)
        and all(
            isinstance(k, str) and k.strip() and (v is None or isinstance(v, str))
            for k, v in record.items()
        )
    )


def match_entities(
    left: Mapping[str, str | None],
    right: Mapping[str, str | None],
    *,
    model: str,
    transport: Transport,
) -> EntityMatchResult:
    """Send explicitly supplied records once; validate the response and fail closed.

    This is a recommendation, not a match approval. All errors return review.
    Input validation happens before invoking transport. No retries occur.
    """
    if not isinstance(model, str) or not _MODEL.fullmatch(model):
        raise ValueError("model must be an exact Jev version, e.g. jev-1.14.0")
    if not _valid_record(left) or not _valid_record(right):
        raise ValueError("records must be non-empty mappings of field names to strings or null")
    payload = {
        "model": model,
        "state": {"left": dict(left), "right": dict(right)},
        "questions": {
            "entity_match": {
                "type": "choice",
                "instructions": "Do these records refer to the same real-world entity?",
                "criteria": {
                    "same_entity": "Evidence supports the same entity.",
                    "different_entity": "Evidence supports different entities.",
                    "needs_review": "Evidence is missing, conflicting, or insufficient to decide.",
                },
            }
        },
    }
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > _MAX_BYTES:
        raise ValueError("request too large")
    try:
        response = transport(payload)
    except Exception:
        return EntityMatchResult("needs_review", None, None, "provider_error")
    try:
        if not isinstance(response, dict) or response.get("model") != model:
            raise ValueError("unexpected model")
        answer = response["answers"]["entity_match"]
        if not isinstance(answer, dict) or answer.get("type") != "choice":
            raise ValueError("unexpected answer type")
        choice, confidence, probabilities = (
            answer["choice"],
            answer["confidence"],
            answer["probabilities"],
        )
        if not isinstance(choice, str) or choice not in _CHOICES:
            raise ValueError("invalid choice")
        if isinstance(confidence, bool) or not isinstance(confidence, (float, int)):
            raise ValueError("invalid confidence")
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("invalid confidence")
        if not isinstance(probabilities, dict) or set(probabilities) != _CHOICES:
            raise ValueError("invalid probabilities")
        if any(
            isinstance(p, bool)
            or not isinstance(p, (float, int))
            or not math.isfinite(p)
            or not 0 <= p <= 1
            for p in probabilities.values()
        ):
            raise ValueError("invalid probabilities")
        if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.01):
            raise ValueError("invalid probability sum")
        if probabilities[choice] < max(probabilities.values()):
            raise ValueError("choice is not most probable")
        return EntityMatchResult(choice, float(confidence), model, "model_decision")
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return EntityMatchResult("needs_review", None, None, "invalid_response")
