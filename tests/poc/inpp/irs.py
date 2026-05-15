"""In++ Realization Artifact: IRS (Intenture Realization Strategy).

Spec source: https://inspark.wiseorg.io (Inspark manifest, schemas/artifacts/IRS)
Full IRS: 10-11 sections, 100%-depth operational plan, internal Inspark team.
PoC subset = key resource/timeline/KPI sections.
"""
from typing import List

from pydantic import BaseModel, Field


class Milestone(BaseModel):
    name: str = Field(..., min_length=3)
    day_offset: int = Field(..., ge=0, description="Days from kickoff")
    owner_agent: str = Field(..., min_length=2, description="AI-agent name (Nick/Hunter/...)")
    deliverable: str = Field(..., min_length=5)


class KPI(BaseModel):
    name: str = Field(..., min_length=2, description="e.g. 'CRUA', 'CR', 'DQ'")
    target_value: str = Field(..., min_length=1, description="e.g. '>80%', '$50K'")
    measurement_window_days: int = Field(..., ge=1)


class IntentureRealizationStrategy(BaseModel):
    artifact_type: str = Field(default="IRS", description="Discriminator")
    schema_version: str = Field(default="2.0.0")
    sp_id: str = Field(..., min_length=1, description="Parent Strategic Proposal reference")

    # Resources
    assigned_agents: List[str] = Field(..., min_length=1, description="AI-agent IDs involved")
    estimated_team_hours: int = Field(..., ge=1)

    # Timeline
    milestones: List[Milestone] = Field(..., min_length=1)
    target_completion_day: int = Field(..., ge=1, le=365)

    # KPIs (success measurement)
    kpis: List[KPI] = Field(..., min_length=1)

    # Risk register summary
    top_risks: List[str] = Field(..., min_length=1, description="Top-N risks")
