SALES_KEYWORDS = {
    "fitness",
    "program",
    "plan",
    "trial",
    "coach",
    "nutrition",
    "weight",
    "membership",
    "subscription",
    "workout",
}


def is_likely_sales_call(text: str, duration_seconds: int | None) -> bool:
    if duration_seconds is not None and duration_seconds < 20:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in SALES_KEYWORDS)
