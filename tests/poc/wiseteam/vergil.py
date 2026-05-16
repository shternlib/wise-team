"""Vergil - S2 WISE coordinator.

A specialized Agno agent + supporting deterministic logic for:
- Lifecycle transitions (via LifecycleFSM)
- Algedonic signal emission on constraint violations
- Readiness verdict per In++ Critical Block Readiness Threshold (CRT)

PoC scope: deterministic decisions wrapped around Claude for narrative output.
Production fork: full Vergil@2.0 semantics from Wise Team Intenture.
"""
from typing import List, Optional

from agno.agent import Agent
from agno.models.anthropic import Claude

from .algedonic import (
    AlgedonicLog,
    AlgedonicSignal,
    EscalationLevel,
    Severity,
)
from .lifecycle import (
    IllegalTransition,
    LifecycleState,
    validate_transition,
)

VERGIL_RBAC_SCOPE = "vergil:coordinator"


class Vergil:
    """Wise Team's S2 coordinator.

    Wraps an Agno agent with Vergil-specific deterministic guards.
    """

    AGENT_INSTRUCTIONS = (
        "You are Vergil, the S2 WISE coordinator for Wise Team. "
        "You ensure intentures progress correctly through their lifecycle, "
        "validate Critical Block Readiness Threshold (CRT), and emit algedonic "
        "signals on constraint violations. Be concise and decisive. "
        "Never invent constraints not provided in the input."
    )

    def __init__(self, model_id: str = "claude-sonnet-4-5") -> None:
        self.scope: str = VERGIL_RBAC_SCOPE
        self.id: str = "vergil"
        self.algedonic_log = AlgedonicLog()
        self._agent = Agent(
            id="vergil",
            model=Claude(id=model_id),
            instructions=self.AGENT_INSTRUCTIONS,
            markdown=False,
        )

    # ─── Lifecycle ────────────────────────────────────────────────────

    def transition(
        self,
        intenture_id: str,
        current: LifecycleState,
        next_state: LifecycleState,
    ) -> LifecycleState:
        """Execute a lifecycle transition. Raises IllegalTransition on invalid step."""
        validate_transition(current, next_state)
        # Production: persist transition in audit log, notify subscribers.
        return next_state

    # ─── CRT - Critical Block Readiness Threshold ─────────────────────

    @staticmethod
    def crt_passes(
        intent_filled: bool,
        object_filled: bool,
        constraints_count: int,
        expected_output_filled: bool,
    ) -> bool:
        """Universal CRT (per In++ §8.1): all 4 Critical Blocks have content."""
        return (
            intent_filled
            and object_filled
            and constraints_count >= 1
            and expected_output_filled
        )

    # ─── Algedonic signal emission ────────────────────────────────────

    def emit_algedonic(
        self,
        severity: Severity,
        message: str,
        intenture_id: str,
        triggering_constraint_type: str,
        escalate_to: Optional[EscalationLevel] = None,
    ) -> AlgedonicSignal:
        """Emit an algedonic signal. Auto-escalate by severity if not specified."""
        if escalate_to is None:
            escalate_to = self._default_escalation_for(severity)
        signal = AlgedonicSignal(
            severity=severity,
            message=message,
            intenture_id=intenture_id,
            triggering_constraint_type=triggering_constraint_type,
            escalate_to=escalate_to,
        )
        self.algedonic_log.emit(signal)
        return signal

    @staticmethod
    def _default_escalation_for(severity: Severity) -> EscalationLevel:
        if severity == Severity.CRITICAL:
            return EscalationLevel.VP
        if severity == Severity.HIGH:
            return EscalationLevel.SL
        return EscalationLevel.PE

    # ─── Narrative output via Agno agent ──────────────────────────────

    def review_summary(self, prompt: str) -> str:
        """Use the underlying agent for narrative explanations."""
        return self._agent.run(prompt).content or ""
