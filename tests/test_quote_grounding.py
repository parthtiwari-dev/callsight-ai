from app.analysis.guardrails import verify_quote_grounding


def test_quote_grounding_accepts_real_quote():
    transcript = [
        "Hi, this is Asha from FitNova.",
        "We can start with a trial session next Tuesday.",
    ]

    result = verify_quote_grounding("trial session next Tuesday", transcript)

    assert result.accepted is True
    assert result.matched_text == transcript[1]


def test_quote_grounding_rejects_hallucinated_quote():
    transcript = [
        "The customer asked about pricing.",
        "The advisor suggested a trial session.",
    ]

    result = verify_quote_grounding("guaranteed to lose ten kilos", transcript)

    assert result.accepted is False
