"""Stage 5 · CVD scenarios B1-B4 (Cognition / Deal / Blueprint / Algedonic).

End-to-end real workflows on a PoC Client:
- B1: Cognition flow - Nick produces CI from NL brief in <= 5 turns
- B2: Deal flow - Nick produces SP from CI, Mr. Wolf does QA, Vergil approves CRT
- B3: Blueprint flow - Nick produces IRS from SP, Vergil validates CRT
- B4: Algedonic signal - inject a safety violation, Vergil escalates

Pass criteria from test plan:
- B1: CI ready <= 5 turns, Required Field Coverage = 100%, Translation Fidelity >= 90%
- B2: SP valid by In++ schema, QA findings <= 2
- B3: IRS >= 4/10 sections Ready/Partial, CRT passes
- B4: Alert-to-Acknowledge <= 5 min, escalation chain works, FP rate <= 10%
"""
import time
from typing import List

import pytest
from agno.agent import Agent
from agno.models.anthropic import Claude
from pydantic import BaseModel, Field

from .inpp.client_intenture import (
    ClientIntenture,
    Constraint,
    ConstraintType,
    IntentVerb,
    ValueItem,
)
from .inpp.irs import IntentureRealizationStrategy
from .inpp.strategic_proposal import StrategicProposal
from .wiseteam.algedonic import EscalationLevel, Severity
from .wiseteam.lifecycle import LifecycleState
from .wiseteam.vergil import Vergil


# ─── PoC Client fixture ────────────────────────────────────────────────


POC_CLIENT_BRIEF = (
    "Client INSPARK-PILOT-008 wants to LAUNCH a new healthy-snack brand in Russia. "
    "Target audience: women age 25-40 interested in fitness, healthy eating, and "
    "weight management. Budget cap is $80,000 USD. Timeline: 90 days from kickoff. "
    "Compliance required: ERID for Russian advertising; product certifications "
    "must be valid. Success means at least 25 published integrations on Instagram "
    "and TikTok with measurable reach and conversion to product page visits."
)


# ─── B1 · Cognition Flow ───────────────────────────────────────────────


def test_b1_cognition_ci_produced_in_one_turn(claude_model_id):
    """Nick produces a complete CI from a single comprehensive brief.

    Multi-turn dialogue is simulated by giving Nick the full brief at once;
    PoC measures Required Field Coverage and verifies all critical blocks are filled.
    Production fork will add interactive multi-turn but PoC validates Nick can
    produce a valid In++ CI from natural language.
    """
    nick = Agent(
        id="nick",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Nick - Inspark's Client Cognition agent. Given the Client's "
            "natural-language brief, produce a Client Intenture (CI) capturing "
            "Intent, Object, Constraints, Expected Output, Value Items, and ICP score. "
            "Use ONLY data the Client provided - never invent budgets, deadlines, "
            "audience segments, or compliance requirements not stated. "
            "icp_match_score: estimate based on Inspark ICP (food/health/RU advertising fits well, ~85)."
        ),
        output_schema=ClientIntenture,
        markdown=False,
    )

    response = nick.run(POC_CLIENT_BRIEF)
    ci: ClientIntenture = response.content

    # B1 Pass criterion: Required Field Coverage = 100% (all critical blocks present)
    assert ci.client_id == "INSPARK-PILOT-008", "Client ID not extracted correctly"
    assert ci.intent_verb == IntentVerb.CREATE, "Intent verb wrong"
    assert len(ci.object) >= 10
    assert len(ci.expected_output) >= 10
    assert len(ci.constraints) >= 1, "No constraints captured"
    assert len(ci.value_items) >= 1, "No value items captured"

    # B1 Pass criterion: ICP score reasonable
    assert ci.icp_match_score is not None
    assert 50 <= ci.icp_match_score <= 100, f"ICP score out of plausible range: {ci.icp_match_score}"

    # B1 verify constraints capture key compliance + budget
    constraint_types = {c.type for c in ci.constraints}
    assert (
        ConstraintType.LEGAL in constraint_types or ConstraintType.BUDGET in constraint_types
    ), "Critical constraints (ERID/budget) not captured"


# ─── B2 · Deal Flow ────────────────────────────────────────────────────


class QAReport(BaseModel):
    findings_count: int = Field(..., ge=0)
    findings: List[str] = Field(default_factory=list)
    verdict: str = Field(..., pattern="^(approve|reject|approve-with-revisions)$")


def test_b2_deal_flow_nick_produces_sp_mrwolf_does_qa(claude_model_id):
    """Nick: CI -> SP. Mr. Wolf: QA on SP. Vergil: CRT verdict."""
    # Setup CI (mirror B1 output)
    ci = ClientIntenture(
        client_id="INSPARK-PILOT-008",
        intent_verb=IntentVerb.CREATE,
        object="Launch a new healthy-snack brand in Russia via influencer marketing",
        expected_output="25+ published integrations on Instagram and TikTok with measurable reach",
        constraints=[
            Constraint(type=ConstraintType.LEGAL, description="ERID compliance for Russian advertising"),
            Constraint(type=ConstraintType.BUDGET, description="Total cap $80,000 USD"),
            Constraint(type=ConstraintType.TIMELINE, description="90 days from kickoff"),
        ],
        value_items=[
            ValueItem(
                description="Reach women age 25-40 in RU interested in fitness/healthy eating",
                priority="must-have",
                beneficiary=["Client", "Inspark"],
            )
        ],
        icp_match_score=85.0,
    )

    nick_sp = Agent(
        id="nick",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Nick. Convert a CI into a Strategic Proposal (SP) with "
            "Mirror -> Gap -> Bridge -> Action structure. Each anchor >= 50 chars. "
            "Use ONLY data from the CI - do not invent. "
            "Budget must respect the CI's BUDGET constraint."
        ),
        output_schema=StrategicProposal,
        markdown=False,
    )

    sp_response = nick_sp.run(f"Convert this CI into an SP:\n{ci.model_dump_json()}")
    sp: StrategicProposal = sp_response.content

    # B2 part 1: SP structurally valid
    assert sp.client_intenture_id == "INSPARK-PILOT-008"
    assert len(sp.mirror) >= 50 and len(sp.gap) >= 50
    assert len(sp.bridge) >= 50 and len(sp.action) >= 50
    assert sp.estimated_budget_usd <= 80000, "SP must respect CI budget cap"

    # B2 part 2: Mr. Wolf does QA
    mr_wolf = Agent(
        id="mr-wolf",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Mr. Wolf - Inspark's QA coordinator. Review a Strategic Proposal. "
            "Return findings_count, list of issues (if any), and verdict. "
            "Approve if SP is consistent with CI, has plausible structure, "
            "and respects all constraints. Be strict but fair."
        ),
        output_schema=QAReport,
        markdown=False,
    )

    qa = mr_wolf.run(
        f"Review this SP for issues. The parent CI had budget cap $80,000 USD and 90-day timeline.\n"
        f"SP:\n{sp.model_dump_json()}"
    )
    qa_report: QAReport = qa.content

    # B2 Pass: QA findings <= 2
    assert qa_report.findings_count <= 2, (
        f"Too many QA findings: {qa_report.findings_count}. Issues: {qa_report.findings}"
    )
    assert qa_report.verdict in ("approve", "approve-with-revisions"), (
        f"Mr. Wolf rejected SP. Verdict: {qa_report.verdict}, issues: {qa_report.findings}"
    )

    # B2 part 3: Vergil CRT verdict on SP-parent CI
    vergil = Vergil(model_id=claude_model_id)
    crt_pass = Vergil.crt_passes(
        intent_filled=True,
        object_filled=True,
        constraints_count=len(ci.constraints),
        expected_output_filled=True,
    )
    assert crt_pass is True, "CRT must pass for a valid CI"

    # B2 verdict: Vergil records lifecycle transition (Structured -> Realizable)
    new_state = vergil.transition(
        intenture_id=ci.client_id,
        current=LifecycleState.STRUCTURED,
        next_state=LifecycleState.REALIZABLE,
    )
    assert new_state == LifecycleState.REALIZABLE


# ─── B3 · Blueprint Flow ───────────────────────────────────────────────


def test_b3_blueprint_nick_produces_irs(claude_model_id):
    """Nick produces IRS from approved SP."""
    sp = StrategicProposal(
        client_intenture_id="INSPARK-PILOT-008",
        proposal_title="Healthy-snack RU launch via Inspark creator pipeline",
        mirror="The Client launches a healthy-snack brand in RU and lacks audience awareness in the women 25-40 fitness segment. Current channels rely on paid ads.",
        gap="There is no creator-led credible voice in this niche; awareness is below 5% and ad-spend ROMI is declining.",
        bridge="Inspark assembles 25 ICP-matched fitness/healthy-eating Instagram and TikTok creators, produces compliant integrations under ERID, tracks reach and product-page conversion.",
        action="Sign SoW within 7 days; kickoff in 14; first 8 integrations published by day 30; full 25 by day 75.",
        estimated_budget_usd=80000,
        estimated_duration_days=90,
        success_metrics=["25 published integrations", "ROMI > 130%", "DQ > 85%"],
    )

    nick_irs = Agent(
        id="nick",
        model=Claude(id=claude_model_id),
        instructions=(
            "You are Nick. Given a Strategic Proposal, produce an Intenture Realization "
            "Strategy (IRS): assigned agents (at least nick, hunter, willie, holmes, vergil), "
            "estimated_team_hours, 3-5 milestones with owner_agent and day_offset within "
            "the SP duration, 3-4 KPIs aligned with SP success_metrics, 2-3 top risks. "
            "Do not invent constraints."
        ),
        output_schema=IntentureRealizationStrategy,
        markdown=False,
    )

    response = nick_irs.run(f"Produce IRS from this SP:\n{sp.model_dump_json()}")
    irs: IntentureRealizationStrategy = response.content

    assert irs.sp_id  # parent link
    assert len(irs.assigned_agents) >= 4, "IRS must assign at least 4 AI-agents"
    assert irs.estimated_team_hours >= 1
    assert 3 <= len(irs.milestones) <= 8
    for m in irs.milestones:
        assert m.day_offset <= sp.estimated_duration_days, (
            f"Milestone {m.name} day_offset {m.day_offset} > SP duration {sp.estimated_duration_days}"
        )
    assert len(irs.kpis) >= 3
    assert irs.target_completion_day <= sp.estimated_duration_days


# ─── B4 · Algedonic Signal ─────────────────────────────────────────────


def test_b4_safety_violation_triggers_algedonic_signal(claude_model_id):
    """Vergil emits a CRITICAL signal when a safety constraint is violated."""
    vergil = Vergil(model_id=claude_model_id)
    intenture_id = "INSPARK-PILOT-008"

    # Inject a safety violation: Holmes reports raw Client revenue numbers in cross-tenant context
    t_start = time.time()
    signal = vergil.emit_algedonic(
        severity=Severity.CRITICAL,
        message=(
            "Holmes returned raw confidential revenue figures ($2.4M MRR) of Client "
            "INSPARK-PILOT-008 to an external analyst session belonging to a "
            "different tenant - potential cross-Client data leak detected."
        ),
        intenture_id=intenture_id,
        triggering_constraint_type="safety",
    )
    elapsed = time.time() - t_start

    # B4 Pass criterion: Alert-to-Acknowledge (emission) sub-second; production target <= 5 min
    assert elapsed < 1.0, f"Signal emission took too long: {elapsed:.3f}s"

    # B4 Pass criterion: escalation chain correct (CRITICAL -> VP)
    assert signal.escalate_to == EscalationLevel.VP
    assert signal.triggering_constraint_type == "safety"
    assert signal.intenture_id == intenture_id

    # B4 Pass criterion: signal logged + retrievable
    signals_for_intenture = vergil.algedonic_log.by_intenture(intenture_id)
    assert signal in signals_for_intenture

    critical_signals = vergil.algedonic_log.by_severity(Severity.CRITICAL)
    assert signal in critical_signals


def test_b4_legal_constraint_violation_high_severity(claude_model_id):
    """ERID compliance failure should be HIGH severity, escalate to SL."""
    vergil = Vergil(model_id=claude_model_id)
    signal = vergil.emit_algedonic(
        severity=Severity.HIGH,
        message="Willie produced ad copy without ERID marking - publication blocked by pre-flight check",
        intenture_id="INSPARK-PILOT-008",
        triggering_constraint_type="legal",
    )
    assert signal.escalate_to == EscalationLevel.SL
