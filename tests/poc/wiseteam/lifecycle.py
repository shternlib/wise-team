"""Intenture Lifecycle FSM.

Per In++ 2.0 spec (Master Release Document, §9 Lifecycle):
    Dream -> Exploratory -> Explicated -> Structured -> Realizable
          -> In Realization -> Evolving -> Archived

Returns can occur (Realizable -> Structured for clarification) so the FSM
is not a strict DAG - it's a graph with allowed transitions.

PoC scope: enforce forward path + Archive-from-any + select returns.
"""
from enum import Enum
from typing import Set


class LifecycleState(str, Enum):
    DREAM = "Dream"
    EXPLORATORY = "Exploratory"
    EXPLICATED = "Explicated"
    STRUCTURED = "Structured"
    REALIZABLE = "Realizable"
    IN_REALIZATION = "In Realization"
    EVOLVING = "Evolving"
    ARCHIVED = "Archived"


# Forward path
_FORWARD = [
    LifecycleState.DREAM,
    LifecycleState.EXPLORATORY,
    LifecycleState.EXPLICATED,
    LifecycleState.STRUCTURED,
    LifecycleState.REALIZABLE,
    LifecycleState.IN_REALIZATION,
    LifecycleState.EVOLVING,
]


def _forward_neighbors(state: LifecycleState) -> Set[LifecycleState]:
    """One step forward on the canonical path."""
    if state not in _FORWARD:
        return set()
    idx = _FORWARD.index(state)
    if idx + 1 < len(_FORWARD):
        return {_FORWARD[idx + 1]}
    return set()


# Selected backward returns (for clarification cycles)
_RETURNS = {
    LifecycleState.STRUCTURED: {LifecycleState.EXPLICATED},
    LifecycleState.REALIZABLE: {LifecycleState.STRUCTURED},
    LifecycleState.IN_REALIZATION: {LifecycleState.REALIZABLE},
    LifecycleState.EVOLVING: {LifecycleState.IN_REALIZATION},
}


class IllegalTransition(Exception):
    """Raised when Vergil attempts an illegal lifecycle transition."""


def allowed_transitions(state: LifecycleState) -> Set[LifecycleState]:
    """Return all valid next states from `state`."""
    allowed: Set[LifecycleState] = set()
    allowed |= _forward_neighbors(state)
    allowed |= _RETURNS.get(state, set())
    # Archive is reachable from any non-Archived state
    if state != LifecycleState.ARCHIVED:
        allowed.add(LifecycleState.ARCHIVED)
    return allowed


def validate_transition(current: LifecycleState, next_state: LifecycleState) -> None:
    """Raise IllegalTransition if next_state not reachable from current."""
    if next_state not in allowed_transitions(current):
        raise IllegalTransition(
            f"Cannot transition from {current.value!r} to {next_state.value!r}. "
            f"Allowed: {sorted(s.value for s in allowed_transitions(current))}"
        )
