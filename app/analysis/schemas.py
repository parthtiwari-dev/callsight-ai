from enum import Enum

from pydantic import BaseModel, Field, model_validator


SCORE_WEIGHTS = {
    "needs_discovery": 0.25,
    "compliance": 0.25,
    "objection_handling": 0.20,
    "product_knowledge": 0.15,
    "next_step_booking": 0.15,
}


class TagType(str, Enum):
    no_needs_discovery = "no_needs_discovery"
    over_promising = "over_promising"
    pressure_or_urgency = "pressure_or_urgency"
    price_before_value = "price_before_value"
    undisclosed_costs = "undisclosed_costs"
    weak_or_missing_trial_booking = "weak_or_missing_trial_booking"
    talking_over_customer = "talking_over_customer"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ScoreDimension(BaseModel):
    score: float = Field(ge=0, le=10)
    rationale: str


class Scores(BaseModel):
    needs_discovery: ScoreDimension
    product_knowledge: ScoreDimension
    objection_handling: ScoreDimension
    compliance: ScoreDimension
    next_step_booking: ScoreDimension

    def weighted_overall(self) -> float:
        total = (
            self.needs_discovery.score * SCORE_WEIGHTS["needs_discovery"]
            + self.compliance.score * SCORE_WEIGHTS["compliance"]
            + self.objection_handling.score * SCORE_WEIGHTS["objection_handling"]
            + self.product_knowledge.score * SCORE_WEIGHTS["product_knowledge"]
            + self.next_step_booking.score * SCORE_WEIGHTS["next_step_booking"]
        )
        return round(total, 2)


class IssueTagOutput(BaseModel):
    tag_type: TagType
    severity: Severity
    timestamp: float | None = None
    quoted_line: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class AnalysisOutput(BaseModel):
    is_sales_call: bool
    summary: str
    scores: Scores
    overall_score: float | None = Field(default=None, ge=0, le=10)
    issues: list[IssueTagOutput] = Field(default_factory=list)
    coaching: list[str] = Field(default_factory=list)
    model_version: str = "mock-analysis-v1"

    @model_validator(mode="after")
    def fill_overall_score(self) -> "AnalysisOutput":
        self.overall_score = self.scores.weighted_overall()
        return self
