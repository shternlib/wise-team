"""A4 · MUST 4 Tool / MCP connectivity test.

Validates Agno's tool calling: Python functions as tools, agent autonomously
picks and invokes them, errors propagate gracefully.

For PoC scope we test custom Python tools (Inspark CRM + billing mocks)
rather than spinning up real MCP servers. MCP server connectivity is a
documented Agno feature (MultiMCPTools, 3-tier MCP) - this test covers
the underlying tool-call mechanism.

Test scenarios:
- A4.1: agent calls a single custom tool successfully
- A4.2: agent picks the correct tool among multiple
- A4.3: tool exception does not crash the agent (graceful degradation)
- A4.4: tool calls are captured in audit trail

Pass criteria (from test plan):
- Tool Call Success Rate >= 95% (binary: each of 3 tools either invoked or not, target 3/3)
- Graceful degradation on tool failures (agent returns answer, not crash)
"""
import pytest
from agno.agent import Agent
from agno.models.anthropic import Claude


# ─── Mock tools - Inspark domain ───────────────────────────────────────


def get_inspark_lead_status(lead_id: str) -> str:
    """Return CRM status for a given Inspark Client lead.

    Args:
        lead_id: Inspark Client lead identifier, e.g. 'INSPARK-LEAD-42'.

    Returns:
        Human-readable status string.
    """
    if lead_id == "FAIL-LEAD":
        raise RuntimeError("Simulated CRM outage for tool-failure test")
    return f"Lead {lead_id}: stage=Cognition (CVD phase 0), ICP score 87%, owner=Nick"


def get_invoice_status(invoice_id: str) -> str:
    """Return billing status for an invoice.

    Args:
        invoice_id: Invoice identifier, e.g. 'INV-2026-005'.

    Returns:
        Human-readable invoice status.
    """
    return f"Invoice {invoice_id}: status=paid, amount=$50000 USD, paid_at=2026-05-01"


def get_github_pr_status(pr_number: int) -> str:
    """Return status of a GitHub PR in the wise-team repo.

    Args:
        pr_number: PR number.

    Returns:
        PR status string.
    """
    return f"PR #{pr_number}: status=open, author=vergil-bot, reviews=1 approved"


# ─── A4.1 · Single tool call ──────────────────────────────────────────


def test_a4_1_agent_calls_single_tool(claude_model_id):
    """Agent given a request that requires a tool must call it and return result."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are a CRM assistant. Always use the get_inspark_lead_status tool "
            "when asked about a lead. Answer in <= 25 words."
        ),
        tools=[get_inspark_lead_status],
        markdown=False,
    )

    response = agent.run("What's the status of lead INSPARK-LEAD-42?")
    answer = (response.content or "").lower()

    assert "inspark-lead-42" in answer or "cognition" in answer or "icp" in answer, (
        f"Agent did not surface tool output. Got: {answer!r}"
    )


# ─── A4.2 · Multiple tools, agent picks correctly ─────────────────────


def test_a4_2_agent_picks_correct_tool_among_three(claude_model_id):
    """Given 3 tools, agent picks the right one based on request."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are an Inspark operations assistant. Always use the appropriate tool. "
            "Answer in <= 20 words."
        ),
        tools=[get_inspark_lead_status, get_invoice_status, get_github_pr_status],
        markdown=False,
    )

    # Ask about a PR - should call get_github_pr_status, NOT lead or invoice
    response = agent.run("What's the status of PR #123 in our wise-team repo?")
    answer = (response.content or "").lower()

    assert "open" in answer or "vergil-bot" in answer or "approved" in answer, (
        f"Agent didn't surface PR tool output. Got: {answer!r}"
    )
    # Shouldn't accidentally mention lead/invoice content
    assert "cognition" not in answer, "Agent called wrong tool (lead instead of PR)"
    assert "paid" not in answer, "Agent called wrong tool (invoice instead of PR)"


# ─── A4.3 · Graceful degradation on tool failure ──────────────────────


def test_a4_3_tool_failure_does_not_crash_agent(claude_model_id):
    """When tool raises, agent must still return a response (graceful degradation)."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are a CRM assistant. Use get_inspark_lead_status when asked. "
            "If the tool errors, tell the user the lookup failed but stay helpful. "
            "Answer in <= 30 words."
        ),
        tools=[get_inspark_lead_status],
        markdown=False,
    )

    # FAIL-LEAD triggers RuntimeError in the tool
    response = agent.run("What's the status of lead FAIL-LEAD?")
    answer = response.content or ""

    # Crash would be exception thrown; we got a response
    assert isinstance(answer, str), f"Expected string response, got {type(answer)}"
    assert len(answer) > 0, "Agent returned empty response on tool failure"


# ─── A4.4 · Tool calls are auditable ──────────────────────────────────


def test_a4_4_tool_calls_in_audit_trail(claude_model_id):
    """Tool calls must be visible in the run's message/tool-call history."""
    agent = Agent(
        model=Claude(id=claude_model_id),
        instructions="Use the tool to answer. <= 15 words.",
        tools=[get_invoice_status],
        markdown=False,
    )

    response = agent.run("Status of invoice INV-2026-005?")

    # Agno run response has .messages with tool_calls embedded
    messages = response.messages or []
    tool_related = [
        m for m in messages
        if (m.role == "tool")
        or (hasattr(m, "tool_calls") and m.tool_calls)
    ]
    assert tool_related, (
        f"No tool-related messages found in audit trail. "
        f"All roles: {[m.role for m in messages]}"
    )
