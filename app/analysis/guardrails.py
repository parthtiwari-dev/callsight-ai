from dataclasses import dataclass

from rapidfuzz import fuzz

from app.analysis.schemas import AnalysisOutput, IssueTagOutput, ScoreDimension, Scores, TagType


@dataclass(frozen=True)
class GroundingResult:
    accepted: bool
    score: float
    matched_text: str | None = None


def normalize_for_match(text: str) -> str:
    return " ".join(text.lower().strip().split())


def verify_quote_grounding(
    quote: str, transcript_lines: list[str], threshold: float = 90.0
) -> GroundingResult:
    normalized_quote = normalize_for_match(quote)
    if not normalized_quote:
        return GroundingResult(False, 0.0)

    best_score = 0.0
    best_line: str | None = None
    for line in transcript_lines:
        score = float(fuzz.partial_ratio(normalized_quote, normalize_for_match(line)))
        if score > best_score:
            best_score = score
            best_line = line

    return GroundingResult(best_score >= threshold, best_score, best_line)


def cap_scores_for_critical_tags(scores: dict[str, float], tags: list[dict]) -> dict[str, float]:
    capped = dict(scores)
    has_critical_compliance_tag = any(
        tag.get("severity") == "critical" and tag.get("tag_type") == "over_promising"
        for tag in tags
    )
    if has_critical_compliance_tag:
        capped["compliance"] = min(float(capped.get("compliance", 10.0)), 3.0)
    return capped


@dataclass(frozen=True)
class GuardrailResult:
    analysis: AnalysisOutput
    rejected_issues: list[IssueTagOutput]


def apply_analysis_guardrails(
    analysis: AnalysisOutput,
    transcript_lines: list[str],
    quote_threshold: float = 90.0,
) -> GuardrailResult:
    accepted: list[IssueTagOutput] = []
    rejected: list[IssueTagOutput] = []

    for issue in analysis.issues:
        grounding = verify_quote_grounding(issue.quoted_line, transcript_lines, quote_threshold)
        if grounding.accepted:
            accepted.append(issue)
        else:
            rejected.append(issue)

    scores = analysis.scores
    has_critical_over_promise = any(
        issue.tag_type == TagType.over_promising and issue.severity.value == "critical"
        for issue in accepted
    )
    if has_critical_over_promise:
        scores = Scores(
            needs_discovery=scores.needs_discovery,
            product_knowledge=scores.product_knowledge,
            objection_handling=scores.objection_handling,
            compliance=ScoreDimension(
                score=min(scores.compliance.score, 3.0),
                rationale=f"{scores.compliance.rationale} Deterministic cap applied because a critical over-promising tag was verified.",
            ),
            next_step_booking=scores.next_step_booking,
        )

    guarded = AnalysisOutput(
        is_sales_call=analysis.is_sales_call,
        summary=analysis.summary,
        scores=scores,
        issues=accepted,
        coaching=analysis.coaching,
        model_version=analysis.model_version,
    )
    return GuardrailResult(guarded, rejected)
