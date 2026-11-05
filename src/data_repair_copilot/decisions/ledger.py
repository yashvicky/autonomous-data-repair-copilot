"""Explicit in-memory ledger for standalone Jev entity-match calls."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import UUID

from data_repair_copilot.decisions.jev_entity import EntityMatchResult, Transport, match_entities


@dataclass(frozen=True)
class LedgerEntry:
    """Metadata only: never contains record values, credentials or provider errors."""

    event_id: UUID
    timestamp: datetime
    route: Literal["jev_entity_match"]
    requested_model: str
    reported_model: str | None
    outcome: Literal["same_entity", "different_entity", "needs_review"]
    confidence: float | None
    review_required: bool
    audit_sample: bool
    cost_usd: None
    cost_status: Literal["unknown"]
    reason: Literal["model_decision", "provider_error", "invalid_response"]


class Ledger(Protocol):
    def append(self, entry: LedgerEntry) -> None: ...


class InMemoryDecisionLedger:
    """Process-local records, not durable or tamper-evident audit storage."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def append(self, entry: LedgerEntry) -> None:
        if not isinstance(entry, LedgerEntry):
            raise ValueError("expected a LedgerEntry")
        if any(previous.event_id == entry.event_id for previous in self._entries):
            raise ValueError("duplicate event ID")
        self._entries.append(entry)

    @property
    def entries(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)


class LedgerWriteError(RuntimeError):
    """A model outcome was withheld because recording failed."""


def match_and_record(
    left: dict[str, str | None],
    right: dict[str, str | None],
    *,
    model: str,
    transport: Transport,
    ledger: Ledger,
    event_id: UUID,
    audit_sample: bool,
) -> EntityMatchResult:
    """Record a single attempted decision before returning it to the caller.

    The caller selects the audit-sample flag. No sample content is stored. Cost
    is unknown: this adapter does not have verified billing data. The ledger
    contains no raw record fields. Existing direct adapter calls bypass this
    wrapper. This function provides no durable or exactly-once guarantee.
    """
    if not isinstance(event_id, UUID) or type(audit_sample) is not bool:
        raise ValueError("event_id must be a UUID and audit_sample must be a bool")
    if not callable(getattr(ledger, "append", None)):
        raise ValueError("ledger must support append")
    if isinstance(ledger, InMemoryDecisionLedger) and any(
        entry.event_id == event_id for entry in ledger.entries
    ):
        raise ValueError("duplicate event ID")
    result = match_entities(left, right, model=model, transport=transport)
    entry = LedgerEntry(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        route="jev_entity_match",
        requested_model=model,
        reported_model=result.model_version,
        outcome=result.outcome,
        confidence=result.confidence,
        review_required=result.outcome == "needs_review",
        audit_sample=audit_sample,
        cost_usd=None,
        cost_status="unknown",
        reason=result.reason,
    )
    try:
        ledger.append(entry)
    except Exception:
        raise LedgerWriteError("decision withheld because ledger recording failed") from None
    return result
