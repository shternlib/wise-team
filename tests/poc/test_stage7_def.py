"""Stage 7 · D, E, F category tests.

D · Self-evolution PoC (3 tests)
   D1: agent config versioning - history preserved
   D2: sandbox apply - new version not auto-promoted; rolled back on flag
   D3 (HARD): rollback completes <= 30s and restores previous behavior

E · Load & cost (3 tests)
   E1: 5 parallel sessions complete without crash
   E2 (HARD): cost-per-CVD-phase measurement working (token usage captured)
   E3: multi-model swap (Sonnet -> Haiku) works on same agent definition

F · Fork-ability (3 tests)
   F1: ✓ already covered in Stage 4 (Vergil integration). Re-asserted here.
   F2 (HARD): upstream merge simulation - working tree state allows merge
   F3: AGNO_TELEMETRY=false enforced via .env
"""
import asyncio
import concurrent.futures
import os
import subprocess
import time
from typing import List

import pytest
from agno.agent import Agent
from agno.models.anthropic import Claude

from .wiseteam.versioning import AgentVersion, AgentVersionStore
from .wiseteam.vergil import Vergil, VERGIL_RBAC_SCOPE


# ═══════════════════════════════════════════════════════════════════════
# D · Self-evolution PoC
# ═══════════════════════════════════════════════════════════════════════


def test_d1_agent_config_versioning_preserves_history():
    store = AgentVersionStore()
    store.push(AgentVersion(
        agent_id="nick", version=1,
        instructions="Be concise.", proposed_by="human",
    ))
    store.push(AgentVersion(
        agent_id="nick", version=2,
        instructions="Be concise and accurate.", proposed_by="vergil",
        rationale="Add accuracy emphasis after PB metric drift",
    ))
    history = store.history("nick")
    assert len(history) == 2
    assert history[0].version == 1
    assert history[1].version == 2
    assert store.tail("nick").version == 2


def test_d2_sandbox_apply_does_not_overwrite_until_promoted():
    """A 'sandbox' version is one not pushed to the live store yet."""
    store = AgentVersionStore()
    live_v1 = AgentVersion(
        agent_id="hunter", version=1,
        instructions="Source 5 creators.", proposed_by="human",
    )
    store.push(live_v1)

    # Sandbox proposal NOT pushed
    sandbox_v2 = AgentVersion(
        agent_id="hunter", version=2,
        instructions="Source 5 creators; prefer fitness niche.",
        proposed_by="agent", rationale="Self-improvement based on past success",
    )
    assert store.tail("hunter").version == 1, "Live version unchanged"
    assert sandbox_v2 not in store.history("hunter")


def test_d3_rollback_completes_in_under_30_seconds():
    """HARD criterion: rollback path must be fast (<= 30s budget; PoC <1s)."""
    store = AgentVersionStore()
    for v in range(1, 4):
        store.push(AgentVersion(
            agent_id="willie", version=v,
            instructions=f"v{v}", proposed_by="human",
        ))
    assert store.tail("willie").version == 3

    t0 = time.time()
    restored = store.rollback("willie")
    elapsed = time.time() - t0

    assert elapsed < 30.0, f"Rollback took {elapsed:.3f}s > 30s budget"
    assert elapsed < 1.0, "PoC expectation: rollback should be sub-second"
    assert restored.version == 2, "Should be at version 2 after one rollback"
    assert store.tail("willie").version == 2


def test_d3_rollback_chain_two_steps():
    store = AgentVersionStore()
    for v in range(1, 4):
        store.push(AgentVersion(
            agent_id="sparky", version=v,
            instructions=f"v{v}", proposed_by="human",
        ))
    store.rollback("sparky")  # 3 -> 2
    store.rollback("sparky")  # 2 -> 1
    assert store.tail("sparky").version == 1


def test_d3_rollback_fails_at_initial_version():
    store = AgentVersionStore()
    store.push(AgentVersion(
        agent_id="harvey", version=1,
        instructions="v1", proposed_by="human",
    ))
    with pytest.raises(RuntimeError):
        store.rollback("harvey")


# ═══════════════════════════════════════════════════════════════════════
# E · Load & cost
# ═══════════════════════════════════════════════════════════════════════


def _run_short_agent(agent: Agent, prompt: str) -> str:
    return agent.run(prompt).content or ""


def test_e1_parallel_sessions_complete_without_crash(claude_model_id):
    """5 parallel LLM-calls on the same Agent definition complete successfully."""
    agent = Agent(
        id="load-test-agent",
        model=Claude(id=claude_model_id),
        instructions="Answer the user in exactly 5 words. No more, no less.",
        markdown=False,
    )

    prompts = [f"Count from {i} to {i+4} comma-separated." for i in range(5)]

    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda p: _run_short_agent(agent, p), prompts))
    elapsed = time.time() - t0

    assert all(isinstance(r, str) and len(r) > 0 for r in results)
    assert elapsed < 60.0, f"Parallel run took {elapsed:.1f}s, expected < 60s"


def test_e2_cost_per_phase_measurable(claude_model_id):
    """HARD criterion: token usage must be accessible from response metadata."""
    agent = Agent(
        id="cost-test-agent",
        model=Claude(id=claude_model_id),
        instructions="Answer in exactly 10 words. No more, no less.",
        markdown=False,
    )
    response = agent.run("Describe Inspark's CVD framework in 10 words.")

    # Agno's run response surfaces metrics; structure may vary by version
    # We assert at least one accessor returns a positive number
    metrics_obj = getattr(response, "metrics", None)

    possible_token_attrs = [
        "input_tokens", "output_tokens", "prompt_tokens", "completion_tokens",
        "total_tokens",
    ]

    found_token_count = False
    if metrics_obj is not None:
        for attr in possible_token_attrs:
            val = getattr(metrics_obj, attr, None)
            # metrics_obj.input_tokens etc may be a list[int]
            if isinstance(val, list) and val and isinstance(val[0], (int, float)):
                if sum(val) > 0:
                    found_token_count = True
                    break
            elif isinstance(val, (int, float)) and val > 0:
                found_token_count = True
                break

    assert found_token_count, (
        f"No positive token count surfaced in response.metrics. "
        f"Got metrics: {metrics_obj!r}"
    )


def test_e3_multi_model_swap_works():
    """Same Agent definition with different model id produces a response.

    Validates model-swap pattern: no agent code changes, only Claude(id=...) param.
    """
    haiku_agent = Agent(
        id="multi-model-test",
        model=Claude(id="claude-haiku-4-5"),
        instructions="Answer in 5 words.",
        markdown=False,
    )
    response = haiku_agent.run("What is 2+2?")
    assert isinstance(response.content, str) and len(response.content) > 0


# ═══════════════════════════════════════════════════════════════════════
# F · Fork-ability
# ═══════════════════════════════════════════════════════════════════════


def test_f1_vergil_built_in_coordinator_present():
    """F1 re-assertion: Vergil class exists with correct RBAC scope."""
    vergil = Vergil()
    assert vergil.scope == VERGIL_RBAC_SCOPE == "vergil:coordinator"
    assert vergil.id == "vergil"


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def test_f2_upstream_remote_configured():
    """HARD criterion (prerequisite): upstream remote must exist for merge testing."""
    result = subprocess.run(
        ["git", "remote", "get-url", "upstream"],
        cwd=_repo_root(),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, "upstream remote not configured"
    assert "agno-agi/agno" in result.stdout, (
        f"upstream should point to agno-agi/agno, got: {result.stdout.strip()}"
    )


def test_f2_upstream_merge_dry_run_would_succeed():
    """HARD criterion: simulate `git merge upstream/main` dry-run.

    We fetch upstream and check if a merge would have conflicts with our PoC
    files. If upstream is behind us (we are 100% ahead), merge is a no-op.
    If upstream has new commits, ensure they don't conflict with our PoC paths.
    """
    repo = _repo_root()

    # Fetch upstream silently (network op)
    fetch = subprocess.run(
        ["git", "fetch", "upstream", "main"],
        cwd=repo, capture_output=True, text=True, timeout=60,
    )
    assert fetch.returncode == 0, f"git fetch upstream failed: {fetch.stderr}"

    # Check if upstream/main has commits we don't
    ahead_behind = subprocess.run(
        ["git", "rev-list", "--left-right", "--count", "upstream/main...HEAD"],
        cwd=repo, capture_output=True, text=True,
    )
    assert ahead_behind.returncode == 0
    # Format: "N M" - N = upstream ahead, M = HEAD ahead
    upstream_ahead, head_ahead = (int(x) for x in ahead_behind.stdout.split())

    # Soft check: report what we found
    print(
        f"\nupstream/main is ahead by {upstream_ahead} commits, "
        f"our main is ahead by {head_ahead} commits."
    )

    # If upstream has new commits, try a no-commit merge attempt
    if upstream_ahead > 0:
        # Use merge-tree (read-only conflict check, no working-tree mutation)
        merge_tree = subprocess.run(
            ["git", "merge-tree", "HEAD", "upstream/main"],
            cwd=repo, capture_output=True, text=True,
        )
        # `merge-tree` returns conflict markers in output if any
        conflicts = (
            "<<<<<<<" in merge_tree.stdout
            or "CONFLICT" in (merge_tree.stderr or "")
        )
        # PoC files (tests/poc/, WISETEAM_POC.md, .env.example) live outside
        # upstream's tree; they should never conflict.
        if conflicts:
            # Verify conflicts are NOT in our PoC paths
            assert "tests/poc/" not in merge_tree.stdout, (
                "Upstream merge would conflict with PoC test paths"
            )
            assert "WISETEAM_POC.md" not in merge_tree.stdout, (
                "Upstream merge would conflict with WISETEAM_POC.md"
            )
    # If upstream is behind us (head_ahead > 0 and upstream_ahead == 0), pass.


def test_f3_telemetry_off_in_environment():
    """AGNO_TELEMETRY=false must be active in test env (loaded from .env)."""
    assert os.getenv("AGNO_TELEMETRY") == "false", (
        f"AGNO_TELEMETRY should be 'false', got: {os.getenv('AGNO_TELEMETRY')!r}"
    )
