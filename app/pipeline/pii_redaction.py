import re

CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){12,19}\b")
PHONE_LIKE_PATTERN = re.compile(r"\b(?:\+?91[- ]?)?[6-9]\d{9}\b")
CODE_CONTEXT_PATTERN = re.compile(
    r"\b((?:verification\s+code|otp|code|pin|passcode)\s*(?:is|:|-|=)?\s*)(\d{4,8})\b",
    re.IGNORECASE,
)


def redact_pii(text: str) -> str:
    redacted = CARD_LIKE_PATTERN.sub("[REDACTED_CARD]", text)
    redacted = PHONE_LIKE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    redacted = CODE_CONTEXT_PATTERN.sub(lambda match: f"{match.group(1)}[REDACTED_CODE]", redacted)
    return redacted
