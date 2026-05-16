"""Algedonic signal mechanism (VSM Beer).

Vergil emits algedonic signals when a constraint violation, safety risk, or
critical anomaly is detected. Signal escalation chain: PE -> SL -> VP.

PoC: in-memory signal log. Production fork will persist in DB + integrate
with notification channels (Slack / email / on-call paging).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationLevel(str, Enum):
    PE = "Product Engineer"
    SL = "Service Lead"
    VP = "Vice President"


@dataclass
class AlgedonicSignal:
    severity: Severity
    message: str
    intenture_id: str
    triggering_constraint_type: str  # safety / legal / quality / ...
    escalate_to: EscalationLevel
    emitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    auto_resolved: bool = False


class AlgedonicLog:
    """In-memory signal store. PoC only."""

    def __init__(self) -> None:
        self._signals: List[AlgedonicSignal] = []

    def emit(self, signal: AlgedonicSignal) -> None:
        self._signals.append(signal)

    def all_signals(self) -> List[AlgedonicSignal]:
        return list(self._signals)

    def by_severity(self, severity: Severity) -> List[AlgedonicSignal]:
        return [s for s in self._signals if s.severity == severity]

    def by_intenture(self, intenture_id: str) -> List[AlgedonicSignal]:
        return [s for s in self._signals if s.intenture_id == intenture_id]

    def latest(self) -> Optional[AlgedonicSignal]:
        return self._signals[-1] if self._signals else None
