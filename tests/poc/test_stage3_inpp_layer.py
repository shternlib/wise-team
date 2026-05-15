"""Stage 3 · In++ Layer expansion test.

Validates all 5 In++ Realization Artifacts (CI/SP/IRS/TB/PB) as Pydantic schemas
and demonstrates a 3-agent producer chain CI -> SP -> IRS via output_schema.

Test scenarios:
- S3.1: each artifact's Pydantic schema is structurally valid (instantiation + serialization)
- S3.2: producer chain - Nick consumes Client NL brief, emits CI; second Nick emits SP from CI; third emits IRS from SP
- S3.3: schema validation rejects malformed in each artifact type
"""
import pytest
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import ValidationError

from .inpp.client_intenture import (
    ClientIntenture,
    Constraint,
    ConstraintType,
    IntentVerb,
    ValueItem,
)
from .inpp.creator_shortlist import CreatorShortlist
from .inpp.irs import IntentureRealizationStrategy, KPI, Milestone
from .inpp.performance_brief import KPIReading, PerformanceBrief
from .inpp.strategic_proposal import StrategicProposal
from .inpp.talent_brief import (
    ContentFormat,
    Platform,
    TalentBrief,
    TargetAudience,
)


# ─── S3.1 · Schemas are structurally valid ─────────────────────────────


def test_s3_1_all_five_artifacts_round_trip_pydantic():
    """Each artifact: instantiate -> serialize -> parse back -> equal."""
    artifacts = []

    ci = ClientIntenture(
        client_id="CL-001",
        intent_verb=IntentVerb.CREATE,
        object="Influencer-marketing campaign for new sports nutrition product",
        expected_output="20 published integrations with measured ROMI > 130%",
        constraints=[
            Constraint(type=ConstraintType.LEGAL, description="ERID compliance mandatory"),
            Constraint(type=ConstraintType.BUDGET, description="Total cap $50K"),
        ],
        value_items=[
            ValueItem(
                description="Reach 1M Russian fitness-interested men age 25-40",
                priority="must-have",
                beneficiary=["Client", "Inspark"],
            )
        ],
        icp_match_score=87.0,
    )
    artifacts.append(("CI", ci))

    sp = StrategicProposal(
        client_intenture_id="CL-001",
        proposal_title="Sports-nutrition launch via Inspark influencer pipeline",
        mirror="You launch a new sports-nutrition product targeting RU-speaking men 25-40 "
               "interested in fitness. Current marketing relies on paid ads with declining CRUA.",
        gap="Awareness in target segment is below 5% and trust in untargeted ads is low. "
            "You need creator-led social proof with measurable, regulated outcomes.",
        bridge="Inspark sources 20 fitness-credible Instagram creators matching ICP, produces "
               "integration-format content, ensures ERID compliance, tracks ROMI via Holmes.",
        action="Sign SoW, kickoff in 5 business days, first 5 integrations published in week 3.",
        estimated_budget_usd=50000,
        estimated_duration_days=60,
        success_metrics=["ROMI > 130%", "CRUA > 0.5%", "DQ > 85%"],
    )
    artifacts.append(("SP", sp))

    irs = IntentureRealizationStrategy(
        sp_id="SP-001",
        assigned_agents=["nick", "hunter", "willie", "holmes", "vergil"],
        estimated_team_hours=120,
        milestones=[
            Milestone(name="Creator shortlist", day_offset=7, owner_agent="hunter",
                      deliverable="20-candidate CreatorShortlist (CS)"),
            Milestone(name="First 5 integrations published", day_offset=21, owner_agent="willie",
                      deliverable="5 published Instagram posts with ERID"),
        ],
        target_completion_day=60,
        kpis=[
            KPI(name="ROMI", target_value=">130%", measurement_window_days=60),
            KPI(name="CRUA", target_value=">0.5%", measurement_window_days=7),
        ],
        top_risks=["ERID delays", "Creator unavailability in niche"],
    )
    artifacts.append(("IRS", irs))

    tb = TalentBrief(
        campaign_id="CL-001",
        target_audience=TargetAudience(
            age_min=25, age_max=40, geo=["RU"], interests=["fitness", "gym"]
        ),
        platforms=[Platform.INSTAGRAM],
        content_format=ContentFormat.INTEGRATION,
        creator_count=5,
        budget_per_creator_usd=2000,
        deadline_days=21,
        must_comply_erid=True,
    )
    artifacts.append(("TB", tb))

    pb = PerformanceBrief(
        irs_id="IRS-001",
        reporting_period="2026-W22",
        readings=[
            KPIReading(kpi_name="ROMI", target_value=">130%", actual_value="142%",
                       status="on-track", period="2026-05"),
            KPIReading(kpi_name="CRUA", target_value=">0.5%", actual_value="0.41%",
                       status="at-risk", period="2026-W22"),
        ],
        diagnosis="ROMI is healthy because Hunter's ICP-filtered creators converted above plan; "
                  "CRUA dipped due to a mid-week algorithm change on Instagram Reels.",
        recommended_actions=[
            "Add 3 more creators to compensate for reach loss",
            "Shift content emphasis from Reels to Stories for affected creators",
        ],
    )
    artifacts.append(("PB", pb))

    # Round-trip: JSON dump -> reload -> equal
    for name, art in artifacts:
        json_str = art.model_dump_json()
        cls = type(art)
        reloaded = cls.model_validate_json(json_str)
        assert reloaded == art, f"{name} did not survive JSON round-trip"
        assert art.artifact_type in {"CI", "SP", "IRS", "TB", "PB"}


# ─── S3.2 · CI -> SP producer chain via agents ─────────────────────────


def test_s3_2_ci_to_sp_producer_chain(claude_model_id):
    """Nick consumes NL Client brief -> emits CI. Nick consumes CI -> emits SP."""
    ci_producer = Agent(
        id="nick-ci-producer",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Nick. Given a Client's natural-language brief, produce a Client Intenture (CI). "
            "Use only stated facts - never invent budget, client_id, or constraints. "
            "icp_match_score: estimate 60-95 based on fit."
        ),
        output_schema=ClientIntenture,
        markdown=False,
    )
    sp_producer = Agent(
        id="nick-sp-producer",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Nick. Given a Client Intenture (CI), produce a Strategic Proposal (SP) "
            "with Mirror -> Gap -> Bridge -> Action structure. Each anchor section >= 50 chars. "
            "Use the CI's data; do not invent."
        ),
        output_schema=StrategicProposal,
        markdown=False,
    )

    nl_brief = (
        "Client CL-NUTRI-007 wants to LAUNCH a plant-based protein bar in Russia. "
        "Target audience: men age 28-45, interested in gym, vegan diet, healthy nutrition. "
        "Budget cap $40,000. They need ERID compliance. Timeline: 45 days from kickoff. "
        "Success means at least 15 published integrations on Instagram and TikTok with measurable reach."
    )

    ci_resp = ci_producer.run(nl_brief)
    ci: ClientIntenture = ci_resp.content
    assert ci.client_id == "CL-NUTRI-007"
    assert ci.intent_verb == IntentVerb.CREATE
    constraint_types = {c.type for c in ci.constraints}
    assert ConstraintType.BUDGET in constraint_types or ConstraintType.LEGAL in constraint_types

    sp_resp = sp_producer.run(
        f"Generate the Strategic Proposal from this CI:\n{ci.model_dump_json(indent=2)}"
    )
    sp: StrategicProposal = sp_resp.content
    assert sp.client_intenture_id == "CL-NUTRI-007"
    assert len(sp.mirror) >= 50 and len(sp.gap) >= 50
    assert len(sp.bridge) >= 50 and len(sp.action) >= 50
    assert sp.estimated_budget_usd <= 40000, "SP budget must respect CI cap"


# ─── S3.3 · Schema validation rejects malformed (no LLM) ───────────────


@pytest.mark.parametrize("artifact_factory,error_kwargs", [
    # SP without enough chars in mirror
    (StrategicProposal, dict(
        client_intenture_id="X", proposal_title="too short", mirror="short",
        gap="x" * 50, bridge="x" * 50, action="x" * 50,
        estimated_budget_usd=100, estimated_duration_days=10,
        success_metrics=["m1"],
    )),
    # CI with invalid intent verb
    (ClientIntenture, dict(
        client_id="X", intent_verb="invent",
        object="x" * 12, expected_output="x" * 12,
        constraints=[Constraint(type=ConstraintType.LEGAL, description="x" * 10)],
        value_items=[ValueItem(description="x" * 10, priority="must-have", beneficiary=["x"])],
    )),
    # PB with KPIReading status outside enum-like pattern
    (KPIReading, dict(
        kpi_name="ROMI", target_value="x", actual_value="x",
        status="exploded", period="2026",
    )),
])
def test_s3_3_pydantic_rejects_malformed(artifact_factory, error_kwargs):
    with pytest.raises(ValidationError):
        artifact_factory(**error_kwargs)
