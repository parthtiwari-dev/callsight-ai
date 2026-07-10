import pytest
from pydantic import ValidationError

from app.analysis.schemas import AnalysisOutput, ScoreDimension, Scores


def build_scores(score: float = 8.0) -> Scores:
    return Scores(
        needs_discovery=ScoreDimension(score=score, rationale="ok"),
        product_knowledge=ScoreDimension(score=score, rationale="ok"),
        objection_handling=ScoreDimension(score=score, rationale="ok"),
        compliance=ScoreDimension(score=score, rationale="ok"),
        next_step_booking=ScoreDimension(score=score, rationale="ok"),
    )


def test_analysis_output_computes_weighted_overall():
    analysis = AnalysisOutput(
        is_sales_call=True,
        summary="summary",
        scores=build_scores(8.0),
        issues=[],
        coaching=[],
    )

    assert analysis.overall_score == 8.0


def test_analysis_output_rejects_invalid_score():
    with pytest.raises(ValidationError):
        ScoreDimension(score=11, rationale="too high")


def test_analysis_output_rejects_unknown_tag_type():
    with pytest.raises(ValidationError):
        AnalysisOutput(
            is_sales_call=True,
            summary="summary",
            scores=build_scores(),
            issues=[
                {
                    "tag_type": "made_up_tag",
                    "severity": "high",
                    "quoted_line": "hello",
                    "reason": "bad",
                    "confidence": 0.8,
                }
            ],
            coaching=[],
        )
