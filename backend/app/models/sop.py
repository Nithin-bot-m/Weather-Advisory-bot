from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FieldThreshold(BaseModel):
    min: Optional[float] = Field(None, description="Minimum inclusive threshold")
    max: Optional[float] = Field(None, description="Maximum inclusive threshold")

    @field_validator("max")
    def validate_range(cls, v, info):
        min_val = info.data.get("min")
        if min_val is not None and v is not None and v < min_val:
            raise ValueError(f"Max threshold ({v}) cannot be less than min threshold ({min_val})")
        return v


class SOP(BaseModel):
    id: str = Field(..., description="Unique SOP ID (e.g. SOP-001)")
    category: str = Field(..., description="Category (outdoor_exercise, travel, vulnerable_groups, recreation)")
    name: str = Field(..., description="Human-readable policy name")
    severity: SeverityLevel = Field(..., description="Severity level: high, medium, low")
    activities: List[str] = Field(..., description="List of activity names/keywords matching this policy")
    conditions: Dict[str, FieldThreshold] = Field(..., description="Weather field threshold conditions")
    advice: str = Field(..., description="Configured safety advice string")
    situational_override: bool = Field(False, description="Whether this SOP is a broad situational override policy")
    eval_type: str = Field("numeric", description="Evaluation mode: numeric or fuzzy")
    suitability_threshold: Optional[float] = Field(None, description="Minimum suitability score for fuzzy SOPs")

    @field_validator("activities")
    def validate_activities(cls, v):
        if not v or len(v) == 0:
            raise ValueError("SOP activities list cannot be empty")
        return [act.lower().strip() for act in v]


class MatchedSOP(BaseModel):
    sop: SOP = Field(..., description="The matched SOP configuration")
    matched_conditions: Dict[str, float] = Field(
        ..., description="Weather field values that triggered the match"
    )
