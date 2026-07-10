from app.analysis.schemas import AnalysisOutput


def analyze_transcript_placeholder(transcript_text: str) -> AnalysisOutput:
    return AnalysisOutput(
        is_sales_call=True,
        summary="Phase 1 placeholder: analysis engine is wired in Phase 2.",
        scores={},
        issues=[],
        coaching=["Run Phase 2 to enable structured OpenAI scoring."],
    )
