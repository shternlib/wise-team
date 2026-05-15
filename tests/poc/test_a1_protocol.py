"""A1 · MUST 1 Protocol Extensibility test.

Validates Agno's ability to enforce custom structured A2A protocols
(In++ 2.0 Realization Artifacts as typed Pydantic schemas).

Test scenarios:
- A1.1: agent produces valid TalentBrief from natural-language brief (output_schema enforced)
- A1.2: TalentBrief consumed by second agent, returns valid CreatorShortlist round-trip
- A1.3: malformed inputs are rejected by Pydantic validation (no LLM call)

Pass criteria (from test plan):
- Schema validation 100%
- Hallucination Rate = 0 on required fields
- Malformed outputs rejected
"""
import pytest
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import ValidationError

from .inpp.creator_shortlist import CreatorShortlist
from .inpp.talent_brief import (
    ContentFormat,
    Platform,
    TalentBrief,
    TargetAudience,
)


# ─── A1.1 · Producer Agent ────────────────────────────────────────────


def test_a1_1_producer_returns_valid_talent_brief(claude_model_id):
    """Agent given NL request must emit a TalentBrief matching the Pydantic schema."""
    producer = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are a Vergil-class coordinator. Given a campaign brief, produce a "
            "TalentBrief (In++ artifact) for the Hunter agent. Be precise. "
            "Use only the data given - never invent campaign IDs, budgets, or audience details."
        ),
        output_schema=TalentBrief,
        markdown=False,
    )

    nl_brief = (
        "Campaign INSPARK-PILOT-001: we are launching a sports nutrition product "
        "targeted at Russian-speaking men age 25-40 interested in fitness, gym, "
        "and protein supplements. Source 5 Instagram creators for integration-style "
        "content. Budget $1500 per creator. We need it shipped in 30 days. "
        "Russian advertising compliance (ERID) is mandatory."
    )

    response = producer.run(nl_brief)
    tb = response.content

    assert isinstance(tb, TalentBrief), f"Expected TalentBrief, got {type(tb)}"
    assert tb.artifact_type == "TB"
    assert tb.campaign_id == "INSPARK-PILOT-001"
    assert tb.creator_count == 5
    assert Platform.INSTAGRAM in tb.platforms
    assert tb.content_format == ContentFormat.INTEGRATION
    assert tb.budget_per_creator_usd == 1500
    assert tb.deadline_days == 30
    assert tb.must_comply_erid is True
    assert tb.target_audience.age_min == 25
    assert tb.target_audience.age_max == 40
    assert "RU" in [g.upper() for g in tb.target_audience.geo]


# ─── A1.2 · Round-trip TB → CS ─────────────────────────────────────────


def test_a1_2_consumer_returns_valid_shortlist(claude_model_id):
    """Hunter agent given a TB must respond with a valid CreatorShortlist."""
    tb = TalentBrief(
        campaign_id="INSPARK-PILOT-001",
        target_audience=TargetAudience(
            age_min=25, age_max=40, geo=["RU"], interests=["fitness", "gym", "nutrition"]
        ),
        platforms=[Platform.INSTAGRAM],
        content_format=ContentFormat.INTEGRATION,
        creator_count=3,
        budget_per_creator_usd=1500,
        deadline_days=30,
        must_comply_erid=True,
    )

    hunter = Agent(
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Hunter - creator-sourcing agent. Given a TalentBrief (In++ artifact), "
            "produce a CreatorShortlist with realistic but FICTIONAL candidates matching the brief. "
            "Use plausible handles (e.g., 'fit_mike_ru'), realistic follower counts (50k-500k), "
            "and engagement rates 0.02-0.08. Provide concise rationale (>=20 chars)."
        ),
        output_schema=CreatorShortlist,
        markdown=False,
    )

    # Pass TB serialized as JSON
    request = (
        f"Source creators per this TalentBrief (JSON):\n"
        f"{tb.model_dump_json(indent=2)}"
    )

    response = hunter.run(request)
    cs = response.content

    assert isinstance(cs, CreatorShortlist), f"Expected CreatorShortlist, got {type(cs)}"
    assert cs.artifact_type == "CS"
    assert cs.talent_brief_id  # not empty
    assert 1 <= len(cs.candidates) <= 10
    assert len(cs.rationale) >= 20
    for cand in cs.candidates:
        assert cand.followers >= 0
        assert 0.0 <= cand.engagement_rate <= 1.0
        assert 0.0 <= cand.icp_match_score <= 100.0


# ─── A1.3 · Schema rejects malformed (no LLM call) ─────────────────────


def test_a1_3_pydantic_rejects_invalid_age_range():
    """age_max=200 must be rejected by Pydantic (validates schema enforcement layer)."""
    with pytest.raises(ValidationError):
        TargetAudience(age_min=25, age_max=200, geo=["RU"], interests=["fitness"])


def test_a1_3_pydantic_rejects_empty_geo():
    """Empty geo list must be rejected."""
    with pytest.raises(ValidationError):
        TargetAudience(age_min=25, age_max=40, geo=[], interests=["fitness"])


def test_a1_3_pydantic_rejects_invalid_platform():
    """Unknown platform must be rejected by Enum."""
    with pytest.raises(ValidationError):
        TalentBrief(
            campaign_id="C1",
            target_audience=TargetAudience(
                age_min=25, age_max=40, geo=["RU"], interests=["fitness"]
            ),
            platforms=["myspace"],  # not in Platform enum
            content_format=ContentFormat.INTEGRATION,
            creator_count=1,
            budget_per_creator_usd=100,
            deadline_days=7,
        )


def test_a1_3_pydantic_rejects_creator_count_out_of_range():
    """creator_count must be 1..200."""
    with pytest.raises(ValidationError):
        TalentBrief(
            campaign_id="C1",
            target_audience=TargetAudience(
                age_min=25, age_max=40, geo=["RU"], interests=["fitness"]
            ),
            platforms=[Platform.INSTAGRAM],
            content_format=ContentFormat.INTEGRATION,
            creator_count=500,  # over max
            budget_per_creator_usd=100,
            deadline_days=7,
        )
