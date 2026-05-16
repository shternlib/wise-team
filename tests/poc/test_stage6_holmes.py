"""Stage 6 · Multi-tenant security with Holmes confidential filter (C1-C3).

Builds on Stage 2 A2 (storage isolation) and adds:
- Same Holmes class instantiated per tenant - each sees only own data
- Cross-tenant query attempt returns empty (defense in depth on top of storage)
- Confidential filter: raw $-amounts and Client-revenue strings redacted; aggregates pass through

Pass criteria (per test plan, C category):
- 0 cross-leaks across tenants
- Holmes confidential filter False Negative rate = 0 (never miss a raw $-amount)
- Aggregates / qualitative analysis pass through filter
"""
import pytest

from .wiseteam.holmes import HOLMES_RBAC_SCOPE, Holmes, confidential_filter


# ─── C1 · Two tenants parallel - each sees own data ──────────────────


def test_c1_two_holmes_instances_per_tenant_scope():
    holmes_a = Holmes(tenant_id="inspark/lead-1")
    holmes_b = Holmes(tenant_id="dragonfamily-poc/lead-1")

    assert holmes_a.tenant_id != holmes_b.tenant_id
    assert holmes_a.scope == holmes_b.scope == HOLMES_RBAC_SCOPE


# ─── C2 · Cross-tenant query refused ──────────────────────────────────


def test_c2_holmes_refuses_cross_tenant_query():
    holmes_a = Holmes(tenant_id="inspark/lead-1")
    # tenant A's Holmes asked about tenant B's data -> empty
    result = holmes_a.cross_tenant_query_returns_empty(
        foreign_tenant_id="dragonfamily-poc/lead-1"
    )
    assert result == "", "Holmes should return empty on cross-tenant query"
    # Same-tenant query allowed
    result_self = holmes_a.cross_tenant_query_returns_empty(
        foreign_tenant_id="inspark/lead-1"
    )
    assert "accessible" in result_self.lower()


# ─── C3 · Confidential filter mechanics (pure unit) ───────────────────


def test_c3_filter_redacts_raw_dollar_amounts():
    # Use a sentence that triggers ONLY the dollar-amount pattern, not the
    # Client-revenue construct (which would replace the whole sentence)
    text = "Q3 totals reached $240,000 USD across active campaigns."
    report = confidential_filter(text)
    assert "$240,000" not in report.output
    assert "[REDACTED]" in report.output
    assert report.confidential_detected is True
    assert report.redactions_count >= 1


def test_c3_filter_redacts_full_client_revenue_sentence():
    """When Client revenue is explicitly named, the construct pattern wins
    and redacts the whole financial assertion (stricter than per-dollar redaction)."""
    text = "Client INSPARK-001's MRR is $240,000 USD this quarter."
    report = confidential_filter(text)
    assert "$240,000" not in report.output
    assert "INSPARK-001" not in report.output
    assert "REDACTED" in report.output
    assert report.confidential_detected is True


def test_c3_filter_redacts_client_revenue_construct():
    text = "Client ACME's revenue grew significantly this year."
    report = confidential_filter(text)
    assert "[REDACTED CLIENT FINANCIALS]" in report.output
    assert report.confidential_detected is True


def test_c3_filter_preserves_aggregate_qualitative_analysis():
    """No raw $-amount or Client-revenue construct -> output unchanged."""
    text = (
        "Across all active campaigns this quarter, average ROMI is on-track at 142%, "
        "with conversion uplift in the women 25-40 fitness segment. "
        "No anomalies detected."
    )
    report = confidential_filter(text)
    assert report.redactions_count == 0
    assert report.output == text
    assert report.confidential_detected is False


def test_c3_filter_preserves_small_amounts_under_threshold():
    """Tiny amounts (under $1000) are not Client-sensitive financials."""
    text = "A $9 SaaS subscription is unrelated to Client confidentiality."
    report = confidential_filter(text)
    assert "$9" in report.output
    assert report.redactions_count == 0


def test_c3_filter_handles_multiple_dollar_amounts():
    text = "Q1 was $50,000 USD, Q2 was $75,000 USD, Q3 was $120,000 USD."
    report = confidential_filter(text)
    assert report.redactions_count == 3
    assert "$50,000" not in report.output
    assert "$75,000" not in report.output
    assert "$120,000" not in report.output


# ─── C3 (integration) · Holmes-via-Claude filtered output ─────────────


def test_c3_holmes_diagnostic_output_filtered(claude_model_id):
    """Holmes given a prompt that would normally surface raw amounts -
    filter must redact them in the returned text."""
    holmes = Holmes(tenant_id="inspark/lead-1", model_id=claude_model_id)
    tenant_data = [
        "Campaign A: revenue $120,000 USD, ROMI 142%",
        "Campaign B: revenue $80,000 USD, ROMI 128%",
        "Campaign C: revenue $50,000 USD, ROMI 115%",
    ]
    report = holmes.query(
        prompt=(
            "Summarize this tenant's quarterly performance in 2 sentences. "
            "Mention the total revenue across campaigns and the average ROMI."
        ),
        tenant_data=tenant_data,
    )

    # Filter must catch any raw $-amounts the LLM might surface
    # (LLM might say "$250,000 total" or "$120,000+$80,000+$50,000")
    import re
    raw_dollars = re.findall(r"\$\s*\d{4,}", report.output)
    # Either no raw amounts OR they were redacted to [REDACTED]
    assert len(raw_dollars) == 0, (
        f"Filter failed: raw $-amounts present in filtered output: {raw_dollars}"
    )
