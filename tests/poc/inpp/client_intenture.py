"""In++ Realization Artifact: CI (Client Intenture).

Spec source: https://inspark.wiseorg.io (Inspark manifest, schemas/artifacts/CI)
Full CI: 17 blocks / 4 layers (Core Definition / Supporting Context /
Development Layer / Readiness Layer). PoC subset = core blocks only.
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IntentVerb(str, Enum):
    CREATE = "create"
    IMPROVE = "improve"
    MAINTAIN = "maintain"
    RESTRUCTURE = "restructure"
    EXPLORE = "explore"
    EXTEND = "extend"
    MIGRATE = "migrate"
    RETIRE = "retire"


class ConstraintType(str, Enum):
    SAFETY = "safety"
    LEGAL = "legal"
    QUALITY = "quality"
    COORDINATION = "coordination"
    BUDGET = "budget"
    TIMELINE = "timeline"
    RESOURCE = "resource"
    SCOPE = "scope"


class Constraint(BaseModel):
    type: ConstraintType
    description: str = Field(..., min_length=5)


class ValueItem(BaseModel):
    description: str = Field(..., min_length=5)
    priority: str = Field(..., pattern="^(must-have|should-have|nice-to-have)$")
    beneficiary: List[str] = Field(..., min_length=1)


class ClientIntenture(BaseModel):
    """Core Definition layer of Client Intenture - PoC subset."""

    artifact_type: str = Field(default="CI", description="Discriminator")
    schema_version: str = Field(default="2.0.0")
    client_id: str = Field(..., min_length=1)
    intent_verb: IntentVerb
    object: str = Field(..., min_length=10, description="What the intent acts upon")
    expected_output: str = Field(..., min_length=10, description="Concrete deliverable")
    constraints: List[Constraint] = Field(..., min_length=1)
    value_items: List[ValueItem] = Field(..., min_length=1)
    icp_match_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
