"""In++ Realization Artifact: PB (Performance Brief).

Spec source: https://inspark.wiseorg.io (Inspark manifest, schemas/artifacts/PB)
Output of Holmes agent - KPI tracking specification.
"""
from typing import List

from pydantic import BaseModel, Field


class KPIReading(BaseModel):
    kpi_name: str = Field(..., min_length=2)
    target_value: str = Field(..., min_length=1)
    actual_value: str = Field(..., min_length=1)
    status: str = Field(..., pattern="^(on-track|at-risk|off-track)$")
    period: str = Field(..., min_length=3, description="e.g. '2026-W20', '2026-05'")


class PerformanceBrief(BaseModel):
    artifact_type: str = Field(default="PB", description="Discriminator")
    schema_version: str = Field(default="2.0.0")
    irs_id: str = Field(..., min_length=1, description="Parent IRS reference")

    reporting_period: str = Field(..., min_length=3)
    readings: List[KPIReading] = Field(..., min_length=1)

    diagnosis: str = Field(
        ..., min_length=30,
        description="Holmes' analysis of why readings are where they are"
    )
    recommended_actions: List[str] = Field(..., min_length=1)
