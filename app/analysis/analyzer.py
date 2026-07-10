import json

from app.analysis.prompts import SYSTEM_PROMPT, build_analysis_prompt
from app.analysis.schemas import AnalysisOutput, ScoreDimension, Scores
from app.config import get_settings
from app.utils.retry import external_api_retry


def mock_analyze_transcript(transcript_text: str, model_version: str = "mock-analysis-v1") -> AnalysisOutput:
    lowered = transcript_text.lower()
    issues = []
    if "cost" in lowered:
        issues.append(
            {
                "tag_type": "price_before_value",
                "severity": "medium",
                "timestamp": 4.4,
                "quoted_line": "Yes, I want to lose weight but I am not sure about the cost.",
                "reason": "The customer raised pricing uncertainty before value was fully developed.",
                "confidence": 0.74,
            }
        )

    return AnalysisOutput(
        is_sales_call=True,
        summary=(
            "The advisor opened the FitNova conversation, identified fitness interest, "
            "heard a cost concern, and suggested a concrete trial session as a next step."
        ),
        scores=Scores(
            needs_discovery=ScoreDimension(
                score=6.0,
                rationale="The advisor checked broad interest but did not yet ask about budget, timeline, or current fitness level.",
            ),
            product_knowledge=ScoreDimension(
                score=6.5,
                rationale="The advisor referenced a plan and trial session but gave limited program detail.",
            ),
            objection_handling=ScoreDimension(
                score=7.0,
                rationale="The cost concern was acknowledged indirectly by suggesting a trial and further discussion.",
            ),
            compliance=ScoreDimension(
                score=9.0,
                rationale="No guarantee, pressure tactic, or hidden-fee claim appears in the transcript.",
            ),
            next_step_booking=ScoreDimension(
                score=8.0,
                rationale="The advisor proposed a trial session next Tuesday, which is a reasonably concrete next step.",
            ),
        ),
        issues=issues,
        coaching=[
            "Ask about the customer's current fitness level, budget, and timeline before describing the plan.",
            "When price anxiety appears, explain value before returning to booking the trial.",
        ],
        model_version=model_version,
    )


@external_api_retry
def openai_analyze_transcript(transcript_text: str, overlap_events: list[dict] | None = None) -> AnalysisOutput:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for real analysis.")

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    schema = AnalysisOutput.model_json_schema()
    response = client.responses.create(
        model=settings.openai_model,
        temperature=0,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_analysis_prompt(transcript_text, overlap_events or []),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "fitnova_call_analysis",
                "schema": schema,
                "strict": True,
            }
        },
    )
    payload = json.loads(response.output_text)
    payload["model_version"] = settings.openai_model
    return AnalysisOutput.model_validate(payload)


def analyze_transcript(
    transcript_text: str,
    overlap_events: list[dict] | None = None,
    *,
    mock: bool = False,
) -> AnalysisOutput:
    settings = get_settings()
    if mock or not settings.openai_api_key:
        return mock_analyze_transcript(transcript_text)
    return openai_analyze_transcript(transcript_text, overlap_events)


def analyze_transcript_placeholder(transcript_text: str) -> AnalysisOutput:
    return mock_analyze_transcript(transcript_text)
