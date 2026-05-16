"""Stage 4 · Vergil as built-in S2 WISE coordinator.

Validates Wise Team-specific layer on top of Agno:
- Lifecycle FSM: forward transitions, valid returns, illegal moves rejected
- CRT (Critical Block Readiness Threshold) verdict
- Algedonic signal emission with severity-based escalation
- Vergil agent class has the right RBAC scope
- Narrative summary via underlying Agno agent
"""
import pytest

from .wiseteam.algedonic import EscalationLevel, Severity
from .wiseteam.lifecycle import (
    IllegalTransition,
    LifecycleState,
    allowed_transitions,
    validate_transition,
)
from .wiseteam.vergil import VERGIL_RBAC_SCOPE, Vergil


# ─── S4.1 · Lifecycle FSM ─────────────────────────────────────────────


def test_s4_1_forward_path_legal():
    """Each forward transition along canonical path must be valid."""
    forward = [
        LifecycleState.DREAM, LifecycleState.EXPLORATORY, LifecycleState.EXPLICATED,
        LifecycleState.STRUCTURED, LifecycleState.REALIZABLE,
        LifecycleState.IN_REALIZATION, LifecycleState.EVOLVING,
    ]
    for i in range(len(forward) - 1):
        validate_transition(forward[i], forward[i + 1])


def test_s4_1_skipping_states_illegal():
    """Dream -> Realizable (skipping) must raise IllegalTransition."""
    with pytest.raises(IllegalTransition):
        validate_transition(LifecycleState.DREAM, LifecycleState.REALIZABLE)


def test_s4_1_archive_from_any_state_allowed():
    for state in LifecycleState:
        if state == LifecycleState.ARCHIVED:
            continue
        assert LifecycleState.ARCHIVED in allowed_transitions(state)


def test_s4_1_select_returns_allowed():
    """Realizable -> Structured (clarification cycle) allowed."""
    validate_transition(LifecycleState.REALIZABLE, LifecycleState.STRUCTURED)


def test_s4_1_arbitrary_backward_illegal():
    """In Realization -> Dream is not a supported return path."""
    with pytest.raises(IllegalTransition):
        validate_transition(LifecycleState.IN_REALIZATION, LifecycleState.DREAM)


# ─── S4.2 · CRT verdict ───────────────────────────────────────────────


def test_s4_2_crt_passes_when_all_filled():
    assert Vergil.crt_passes(
        intent_filled=True,
        object_filled=True,
        constraints_count=3,
        expected_output_filled=True,
    ) is True


def test_s4_2_crt_fails_on_missing_constraint():
    assert Vergil.crt_passes(
        intent_filled=True,
        object_filled=True,
        constraints_count=0,
        expected_output_filled=True,
    ) is False


def test_s4_2_crt_fails_on_missing_expected_output():
    assert Vergil.crt_passes(
        intent_filled=True,
        object_filled=True,
        constraints_count=2,
        expected_output_filled=False,
    ) is False


# ─── S4.3 · Algedonic signal emission ─────────────────────────────────


def test_s4_3_emit_high_severity_escalates_to_sl():
    vergil = Vergil()
    sig = vergil.emit_algedonic(
        severity=Severity.HIGH,
        message="Hunter cannot source creators within ICP score >= 80",
        intenture_id="inspark/lead-42",
        triggering_constraint_type="quality",
    )
    assert sig.escalate_to == EscalationLevel.SL
    assert sig in vergil.algedonic_log.all_signals()


def test_s4_3_emit_critical_severity_escalates_to_vp():
    vergil = Vergil()
    sig = vergil.emit_algedonic(
        severity=Severity.CRITICAL,
        message="Suspected cross-Client data leak in Holmes diagnostic output",
        intenture_id="inspark/lead-42",
        triggering_constraint_type="safety",
    )
    assert sig.escalate_to == EscalationLevel.VP


def test_s4_3_emit_low_severity_escalates_to_pe():
    vergil = Vergil()
    sig = vergil.emit_algedonic(
        severity=Severity.LOW,
        message="DQ slightly below target (84% vs >=85%)",
        intenture_id="inspark/lead-42",
        triggering_constraint_type="quality",
    )
    assert sig.escalate_to == EscalationLevel.PE


def test_s4_3_signal_log_queryable_by_intenture():
    vergil = Vergil()
    vergil.emit_algedonic(
        severity=Severity.MEDIUM, message="m1",
        intenture_id="A", triggering_constraint_type="quality",
    )
    vergil.emit_algedonic(
        severity=Severity.MEDIUM, message="m2",
        intenture_id="B", triggering_constraint_type="quality",
    )
    assert len(vergil.algedonic_log.by_intenture("A")) == 1
    assert len(vergil.algedonic_log.by_intenture("B")) == 1
    assert len(vergil.algedonic_log.by_intenture("C")) == 0


# ─── S4.4 · RBAC scope and identity ───────────────────────────────────


def test_s4_4_vergil_has_correct_scope():
    vergil = Vergil()
    assert vergil.scope == VERGIL_RBAC_SCOPE == "vergil:coordinator"
    assert vergil.id == "vergil"


# ─── S4.5 · Narrative review via underlying agent ─────────────────────


def test_s4_5_vergil_can_produce_narrative_review(claude_model_id):
    """Vergil uses Claude for narrative summaries when needed."""
    vergil = Vergil(model_id=claude_model_id)
    summary = vergil.review_summary(
        "In 20 words: an intenture has Intent and Object filled but Constraints empty. "
        "Has CRT passed? Just yes/no with one-sentence reason."
    )
    assert isinstance(summary, str)
    assert len(summary) > 5
    assert ("no" in summary.lower()) or ("not" in summary.lower()), (
        "Vergil should conclude CRT has NOT passed when constraints empty"
    )
