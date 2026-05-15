"""In++ Realization Artifact: TB (Talent Brief).

Spec source: https://inspark.wiseorg.io (Inspark namespace manifest, schemas/artifacts/TB)
PoC scope: minimal viable subset (~7 fields) sufficient for A1 round-trip validation.
Production fork will mirror full TB schema.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Platform(str, Enum):
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TELEGRAM = "telegram"
    VK = "vk"


class ContentFormat(str, Enum):
    INTEGRATION = "integration"
    REVIEW = "review"
    UNBOXING = "unboxing"
    TUTORIAL = "tutorial"
    NATIVE_AD = "native_ad"


class TargetAudience(BaseModel):
    """Audience demographics + psychographics."""

    age_min: int = Field(..., ge=13, le=80, description="Min age, 13-80")
    age_max: int = Field(..., ge=13, le=80, description="Max age, 13-80")
    geo: List[str] = Field(..., min_length=1, description="ISO country codes, e.g. ['RU', 'BY']")
    interests: List[str] = Field(..., min_length=1, description="2-5 interest topics")


class TalentBrief(BaseModel):
    """In++ Realization Artifact for Hunter agent (creator sourcing)."""

    artifact_type: str = Field(default="TB", description="Discriminator - always 'TB'")
    schema_version: str = Field(default="2.0.0")
    campaign_id: str = Field(..., min_length=1, description="Reference to parent CVD campaign")
    target_audience: TargetAudience = Field(..., description="Whom we want to reach")
    platforms: List[Platform] = Field(..., min_length=1, description="Where creators must operate")
    content_format: ContentFormat = Field(..., description="Type of content expected")
    creator_count: int = Field(..., ge=1, le=200, description="How many creators to source")
    budget_per_creator_usd: int = Field(..., ge=10, description="Max USD per creator")
    deadline_days: int = Field(..., ge=1, le=180, description="Days from now")
    must_comply_erid: bool = Field(default=False, description="Russian advertising marking required")
    additional_constraints: Optional[List[str]] = Field(default=None, description="Free-form")
