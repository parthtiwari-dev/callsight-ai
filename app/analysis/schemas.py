from pydantic import BaseModel, Field


class ScoreDimension(BaseModel):
    score: float = Field(ge=0, le=10)
    rationale: str


class IssueTagOutput(BaseModel):
    tag_type: str
    severity: str
    timestamp: float | None = None
    quoted_line: str
    reason: str
    confidence: float = Field(ge=0, le=1)


class AnalysisOutput(BaseModel):
    is_sales_call: bool
    summary: str
    scores: dict[str, ScoreDimension]
    issues: list[IssueTagOutput] = Field(default_factory=list)
    coaching: list[str] = Field(default_factory=list)
