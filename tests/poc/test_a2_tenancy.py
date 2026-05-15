"""A2 · MUST 2 Multi-tenancy test.

Validates Agno's data isolation between tenants on storage layer.
Per Wise Team requirement: namespace + per-tenant isolation in data model,
not retrofit.

Test scenarios:
- A2.1: agent runs scoped to two different user_ids create separate sessions
- A2.2: cross-tenant session query returns empty (tenant-B cannot read tenant-A sessions)
- A2.3: memory created by tenant-A is not visible to tenant-B (via memory_manager)

Pass criteria (from test plan):
- 0 cross-leaks
- Memory query from B returns empty
- RBAC-scopes enforcement works per request
"""
import tempfile
from pathlib import Path

import pytest
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude


@pytest.fixture(scope="module")
def shared_db():
    """SqliteDb shared between the two tenants (proves isolation despite shared storage)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    yield SqliteDb(db_file=tmp.name)
    Path(tmp.name).unlink(missing_ok=True)


# Tenant identifiers - same pattern as Wise Team namespace `<org>/<project>`
TENANT_A_USER = "inspark/lead-1"
TENANT_B_USER = "dragonfamily-poc/lead-1"


# ─── A2.1 · Two tenants, isolated sessions ────────────────────────────


def test_a2_1_two_tenants_create_separate_sessions(shared_db, claude_model_id):
    """Agent runs for two user_ids must produce separate session records in DB."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions="You are a brief assistant. Answer in <= 10 words.",
        db=shared_db,
        markdown=False,
    )

    # Tenant A run
    agent.run(
        "My campaign budget is exactly 50000 USD. Confirm in 5 words.",
        user_id=TENANT_A_USER,
        session_id="tenant-a-session-1",
    )

    # Tenant B run - same agent, different user
    agent.run(
        "My campaign budget is exactly 90000 USD. Confirm in 5 words.",
        user_id=TENANT_B_USER,
        session_id="tenant-b-session-1",
    )

    # Direct DB query: sessions for each tenant
    sessions_a = shared_db.get_sessions(user_id=TENANT_A_USER)
    sessions_b = shared_db.get_sessions(user_id=TENANT_B_USER)

    assert len(sessions_a) >= 1, "Tenant A should have at least 1 session"
    assert len(sessions_b) >= 1, "Tenant B should have at least 1 session"

    # Cross-check: A's sessions don't contain B's session_id and vice versa
    a_session_ids = {s.session_id for s in sessions_a}
    b_session_ids = {s.session_id for s in sessions_b}

    assert "tenant-a-session-1" in a_session_ids
    assert "tenant-b-session-1" in b_session_ids
    assert "tenant-b-session-1" not in a_session_ids, "Cross-tenant session leak (A sees B)"
    assert "tenant-a-session-1" not in b_session_ids, "Cross-tenant session leak (B sees A)"


# ─── A2.2 · Tenant-B cannot query tenant-A's sessions ─────────────────


def test_a2_2_tenant_b_cannot_read_tenant_a_sessions(shared_db):
    """Direct query as tenant B must not surface tenant A's session data."""
    # Test depends on A2.1 having created sessions; module-scoped fixture
    sessions_for_b = shared_db.get_sessions(user_id=TENANT_B_USER)

    # None of tenant B's sessions should contain Tenant A's budget marker
    for sess in sessions_for_b:
        runs = sess.runs or []
        for run in runs:
            messages = run.messages or []
            for msg in messages:
                content = (msg.content or "").lower() if hasattr(msg, "content") else ""
                assert "50000" not in content, (
                    f"Cross-tenant content leak: tenant B's session "
                    f"{sess.session_id} contains tenant A's '50000' marker"
                )


# ─── A2.3 · Cross-tenant content not retrievable via agent re-run ─────


def test_a2_3_agent_does_not_recall_other_tenants_data(shared_db, claude_model_id):
    """When tenant B asks about their budget in a NEW session, agent must not leak
    tenant A's budget (50000) - it must only see its own user history."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are a brief assistant. If the user asks about their budget, "
            "answer only based on what THIS USER told you. If you don't know, "
            "say 'unknown'."
        ),
        db=shared_db,
        add_history_to_context=True,
        num_history_runs=10,
        markdown=False,
    )

    # Re-run as tenant B (new session) - asking about budget
    response = agent.run(
        "What budget did I tell you? Just the number or 'unknown'.",
        user_id=TENANT_B_USER,
        session_id="tenant-b-session-2",
    )
    answer = (response.content or "").lower()

    # Tenant B told us 90000, NOT 50000 (which was tenant A's)
    assert "50000" not in answer, (
        f"Tenant B's agent recalled tenant A's '50000' budget. Cross-leak. Got: {answer!r}"
    )
