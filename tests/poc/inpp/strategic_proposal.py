"""In++ Realization Artifact: SP (Strategic Proposal).

Spec source: https://inspark.wiseorg.io (Inspark manifest, schemas/artifacts/SP)
Pattern: Mirror -> Gap -> Bridge -> Action (4 anchor sections of 11 total).
PoC subset = 4 anchor sections + summary fields.
"""
from typing import List

from pydantic import BaseModel, Field


class StrategicProposal(BaseModel):
    artifact_type: str = Field(default="SP", description="Discriminator")
    schema_version: str = Field(default="2.0.0")
    client_intenture_id: str = Field(..., min_length=1, description="Parent CI reference")
    proposal_title: str = Field(..., min_length=5)

    # 4 anchor sections (Mirror -> Gap -> Bridge -> Action)
    mirror: str = Field(
        ..., min_length=50,
        description="Reflect Client's current state - what we observed"
    )
    gap: str = Field(
        ..., min_length=50,
        description="What stands between current and desired state"
    )
    bridge: str = Field(
        ..., min_length=50,
        description="Our strategic approach to close the gap"
    )
    action: str = Field(
        ..., min_length=50,
        description="Concrete next steps the Client takes after approval"
    )

    # Summary fields
    estimated_budget_usd: int = Field(..., ge=0)
    estimated_duration_days: int = Field(..., ge=1, le=365)
    success_metrics: List[str] = Field(..., min_length=1, description="KPI list")
