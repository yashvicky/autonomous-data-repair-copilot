from uuid import UUID, uuid4

import pytest

from data_repair_copilot.decisions.ledger import (
    InMemoryDecisionLedger,
    LedgerWriteError,
    match_and_record,
)

MODEL = "jev-1.14.0"


def response():
    return {
        "model": MODEL,
        "answers": {
            "entity_match": {
                "type": "choice",
                "choice": "same_entity",
                "confidence": 0.56,
                "probabilities": {"same_entity": 0.8, "different_entity": 0.1, "needs_review": 0.1},
            }
        },
    }


def test_logged_match() -> None:
    ledger = InMemoryDecisionLedger()
    event_id = uuid4()
    result = match_and_record(
        {"name": "SYNTHETIC_PERSON_A"},
        {"name": "SYNTHETIC_PERSON_B"},
        model=MODEL,
        transport=lambda payload: response(),
        ledger=ledger,
        event_id=event_id,
        audit_sample=True,
    )
    entry = ledger.entries[0]
    assert (result.outcome, entry.outcome, entry.confidence) == ("same_entity", "same_entity", 0.56)
    assert (entry.route, entry.requested_model, entry.reported_model) == (
        "jev_entity_match",
        MODEL,
        MODEL,
    )
    assert entry.event_id == event_id and entry.timestamp.utcoffset().total_seconds() == 0
    assert entry.audit_sample is True and entry.review_required is False
    assert entry.cost_status == "unknown" and entry.cost_usd is None
    assert "SYNTHETIC_PERSON" not in repr(entry)


def test_failure_record() -> None:
    def broken(payload):
        raise RuntimeError("PRIVATE_ERROR")

    ledger = InMemoryDecisionLedger()
    result = match_and_record(
        {"name": "SYNTHETIC_PERSON_A"},
        {"name": "SYNTHETIC_PERSON_B"},
        model=MODEL,
        transport=broken,
        ledger=ledger,
        event_id=uuid4(),
        audit_sample=False,
    )
    entry = ledger.entries[0]
    assert result.outcome == "needs_review" and entry.review_required
    assert (entry.reason, entry.confidence, entry.reported_model) == ("provider_error", None, None)
    assert entry.cost_status == "unknown" and entry.cost_usd is None
    assert "PRIVATE_ERROR" not in repr(entry) and "SYNTHETIC_PERSON" not in repr(entry)


def test_fail_closed() -> None:
    calls = []

    def transport(payload):
        calls.append(payload)
        return response()

    ledger = InMemoryDecisionLedger()
    for bad_id, flag in (("not-a-uuid", True), (uuid4(), 1)):
        with pytest.raises(ValueError):
            match_and_record(
                {"id": "a"},
                {"id": "b"},
                model=MODEL,
                transport=transport,
                ledger=ledger,
                event_id=bad_id,
                audit_sample=flag,
            )
    assert calls == []

    class FailingLedger:
        def append(self, entry):
            raise RuntimeError("PRIVATE_ERROR")

    with pytest.raises(LedgerWriteError, match="decision withheld") as failure:
        match_and_record(
            {"id": "a"},
            {"id": "b"},
            model=MODEL,
            transport=transport,
            ledger=FailingLedger(),
            event_id=UUID(int=0),
            audit_sample=False,
        )
    assert len(calls) == 1 and "PRIVATE_ERROR" not in str(failure.value)
    assert failure.value.__suppress_context__ is True


def test_duplicate_event_rejected_before_call() -> None:
    ledger = InMemoryDecisionLedger()
    event_id = uuid4()
    calls = []

    def transport(payload):
        calls.append(payload)
        return response()

    for attempt in range(2):
        if attempt:
            with pytest.raises(ValueError, match="duplicate event ID"):
                match_and_record(
                    {"id": "a"},
                    {"id": "b"},
                    model=MODEL,
                    transport=transport,
                    ledger=ledger,
                    event_id=event_id,
                    audit_sample=False,
                )
        else:
            match_and_record(
                {"id": "a"},
                {"id": "b"},
                model=MODEL,
                transport=transport,
                ledger=ledger,
                event_id=event_id,
                audit_sample=False,
            )
    assert len(calls) == 1
