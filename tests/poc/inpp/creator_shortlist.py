"""In++ derived response: CreatorShortlist.

Mock structure for A1 round-trip - Hunter responds to TalentBrief with shortlist.
Production CS Realization Artifact will follow Inspark schema.
"""
from typing import List

from pydantic import BaseModel, Field


class CreatorCandidate(BaseModel):
    handle: str = Field(..., description="Creator handle without @")
    platform: str = Field(..., description="instagram, youtube, tiktok, telegram, vk")
    followers: int = Field(..., ge=0)
    engagement_rate: float = Field(..., ge=0.0, le=1.0, description="0..1")
    estimated_price_usd: int = Field(..., ge=0)
    icp_match_score: float = Field(..., ge=0.0, le=100.0, description="ICP scorecard score 0-100")
    notes: str = Field(default="", description="Why selected")


class CreatorShortlist(BaseModel):
    artifact_type: str = Field(default="CS", description="Discriminator - always 'CS'")
    schema_version: str = Field(default="2.0.0")
    talent_brief_id: str = Field(..., description="Reference to source TB")
    candidates: List[CreatorCandidate] = Field(
        ..., min_length=1, max_length=10, description="Selected creators"
    )
    rationale: str = Field(..., min_length=20, description="Why these candidates")
