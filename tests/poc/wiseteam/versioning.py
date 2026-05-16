"""Agent configuration versioning + rollback (PoC for self-evolution).

Per Wise Team Intenture V-evolve: AI-agents may modify their own
configuration (instructions, tools), but all changes are versioned with
guaranteed rollback in case of regression.

PoC scope: in-memory version store. Production: persistent in AgentOS DB
with canary deploy + automatic rollback on metric degradation.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentVersion:
    agent_id: str
    version: int
    instructions: str
    proposed_by: str  # "human" / "agent" / "vergil"
    rationale: str = ""
    created_at: float = field(default_factory=time.time)


class AgentVersionStore:
    """Per-agent stack of versions. The most recent active version is .tail()."""

    def __init__(self) -> None:
        self._stacks: Dict[str, List[AgentVersion]] = {}

    def push(self, version: AgentVersion) -> None:
        stack = self._stacks.setdefault(version.agent_id, [])
        if stack and version.version != stack[-1].version + 1:
            raise ValueError(
                f"Version number must be monotonic; got {version.version} after {stack[-1].version}"
            )
        stack.append(version)

    def tail(self, agent_id: str) -> Optional[AgentVersion]:
        stack = self._stacks.get(agent_id, [])
        return stack[-1] if stack else None

    def history(self, agent_id: str) -> List[AgentVersion]:
        return list(self._stacks.get(agent_id, []))

    def rollback(self, agent_id: str) -> AgentVersion:
        """Pop the latest version, return the one now active.

        Raises if there's nothing to roll back to.
        """
        stack = self._stacks.get(agent_id, [])
        if len(stack) < 2:
            raise RuntimeError(
                f"Cannot rollback agent {agent_id!r}: only {len(stack)} version(s) exist"
            )
        stack.pop()
        return stack[-1]
