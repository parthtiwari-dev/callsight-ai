from dataclasses import dataclass

from rapidfuzz import fuzz


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
