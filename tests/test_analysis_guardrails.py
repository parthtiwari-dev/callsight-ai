from app.analysis.guardrails import apply_analysis_guardrails
from app.analysis.schemas import AnalysisOutput, ScoreDimension, Scores


def scores(compliance: float = 9.0) -> Scores:
    return Scores(
        needs_discovery=ScoreDimension(score=8, rationale="ok"),
        product_knowledge=ScoreDimension(score=8, rationale="ok"),
        objection_handling=ScoreDimension(score=8, rationale="ok"),
        compliance=ScoreDimension(score=compliance, rationale="ok"),
        next_step_booking=ScoreDimension(score=8, rationale="ok"),
    )


def test_guardrails_reject_hallucinated_issue():
    analysis = AnalysisOutput(
        is_sales_call=True,
        summary="summary",
        scores=scores(),
        issues=[
            {
                "tag_type": "pressure_or_urgency",
                "severity": "high",
                "quoted_line": "This offer expires in ten minutes",
                "reason": "urgency",
                "confidence": 0.9,
            }
        ],
        coaching=[],
    )

    result = apply_analysis_guardrails(analysis, ["We can start with a trial session next Tuesday."])

    assert result.analysis.issues == []
    assert len(result.rejected_issues) == 1


def test_guardrails_caps_compliance_for_grounded_critical_over_promising():
    analysis = AnalysisOutput(
        is_sales_call=True,
        summary="summary",
        scores=scores(compliance=9),
        issues=[
            {
                "tag_type": "over_promising",
                "severity": "critical",
                "quoted_line": "You will definitely lose ten kilos.",
                "reason": "guaranteed result",
                "confidence": 0.95,
            }
        ],
        coaching=[],
    )

    result = apply_analysis_guardrails(analysis, ["You will definitely lose ten kilos."])

    assert len(result.analysis.issues) == 1
    assert result.analysis.scores.compliance.score == 3.0
    assert result.analysis.overall_score < analysis.overall_score
