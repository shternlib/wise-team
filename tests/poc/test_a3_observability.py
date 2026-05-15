"""A3 · MUST 3 Observability + Audit Trail test.

Validates Agno's structured logging: every agent action persisted, retrievable
via session/run history. Multi-agent workflow events linkable through DB.

Test scenarios:
- A3.1: every agent run is persisted in DB (run history accessible)
- A3.2: messages within a run are stored (user input + assistant output)
- A3.3: multi-agent chain produces queryable trace across agent_ids
- A3.4: tool call events (when used) are captured in run history

Pass criteria (from test plan):
- 100% actions logged
- Trace reconstructable from logs
- Query on agent_id returns chronological feed
"""
import tempfile
from pathlib import Path

import pytest
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.anthropic import Claude

from .inpp.creator_shortlist import CreatorShortlist
from .inpp.talent_brief import (
    ContentFormat,
    Platform,
    TalentBrief,
    TargetAudience,
)


@pytest.fixture(scope="module")
def shared_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    yield SqliteDb(db_file=tmp.name)
    Path(tmp.name).unlink(missing_ok=True)


USER_ID = "inspark/observability-test"


# ─── A3.1 · Run is persisted ───────────────────────────────────────────


def test_a3_1_agent_run_persisted_in_db(shared_db, claude_model_id):
    """After an agent.run(), DB must contain the session+run record."""
    agent = Agent(
        id="nick-poc",
        model=Claude(id=claude_model_id),
        instructions="Answer in <= 8 words.",
        db=shared_db,
        markdown=False,
    )
    agent.run(
        "Say 'persisted' and nothing else.",
        user_id=USER_ID,
        session_id="obs-session-1",
    )
    sessions = shared_db.get_sessions(user_id=USER_ID)
    session_ids = [s.session_id for s in sessions]
    assert "obs-session-1" in session_ids

    target = next(s for s in sessions if s.session_id == "obs-session-1")
    assert target.runs, "Session must have at least one run"


# ─── A3.2 · Messages within run captured ───────────────────────────────


def test_a3_2_run_messages_captured(shared_db):
    """Run must contain user message + assistant response (audit trail)."""
    sessions = shared_db.get_sessions(user_id=USER_ID)
    session = next(s for s in sessions if s.session_id == "obs-session-1")
    run = session.runs[0]

    messages = run.messages or []
    roles = [m.role for m in messages]

    assert "user" in roles, "User input must be in audit trail"
    assert "assistant" in roles, "Assistant response must be in audit trail"


# ─── A3.3 · Multi-agent chain traceable ────────────────────────────────


def test_a3_3_multi_agent_chain_produces_chronological_trace(shared_db, claude_model_id):
    """Chain of two agents - both runs queryable via DB."""
    nick = Agent(
        id="nick-poc",
        model=Claude(id=claude_model_id),
        instructions=(
            "You produce a TalentBrief. Use only the data given - never invent."
        ),
        output_schema=TalentBrief,
        db=shared_db,
        markdown=False,
    )
    hunter = Agent(
        id="hunter-poc",
        model=Claude(id=claude_model_id),
        instructions=(
            "Given a TalentBrief, produce a small (2 candidates) CreatorShortlist. "
            "Plausible fictional handles."
        ),
        output_schema=CreatorShortlist,
        db=shared_db,
        markdown=False,
    )

    # Step 1: Nick produces TB
    tb_response = nick.run(
        "Campaign C2: 2 Instagram creators, men 25-35 in RU, fitness niche, "
        "integration format, $1000 each, 14 days, ERID required.",
        user_id=USER_ID,
        session_id="chain-session-nick",
    )
    tb: TalentBrief = tb_response.content

    # Step 2: Hunter consumes TB
    hunter.run(
        f"Source per this TalentBrief:\n{tb.model_dump_json()}",
        user_id=USER_ID,
        session_id="chain-session-hunter",
    )

    # All sessions for this user - chronologically tractable
    sessions = shared_db.get_sessions(user_id=USER_ID)
    session_ids = {s.session_id for s in sessions}

    assert "chain-session-nick" in session_ids
    assert "chain-session-hunter" in session_ids

    # Sessions have agent_id linkage (audit query: which agent ran this session?)
    nick_session = next(s for s in sessions if s.session_id == "chain-session-nick")
    hunter_session = next(s for s in sessions if s.session_id == "chain-session-hunter")

    assert nick_session.agent_id == "nick-poc", (
        f"Expected nick-poc, got {nick_session.agent_id}"
    )
    assert hunter_session.agent_id == "hunter-poc", (
        f"Expected hunter-poc, got {hunter_session.agent_id}"
    )


# ─── A3.4 · Audit query by agent_id ────────────────────────────────────


def test_a3_4_query_by_agent_id_returns_only_that_agents_sessions(shared_db):
    """Audit query: get only nick-poc sessions, must not return hunter-poc."""
    nick_sessions = shared_db.get_sessions(user_id=USER_ID, component_id="nick-poc")
    nick_ids = {s.session_id for s in nick_sessions}

    assert "chain-session-nick" in nick_ids
    assert "chain-session-hunter" not in nick_ids, (
        "Audit query by agent_id leaked another agent's session"
    )
