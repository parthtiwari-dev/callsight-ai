import re

CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){12,19}\b")
OTP_LIKE_PATTERN = re.compile(r"\b\d{4,8}\b")
PHONE_LIKE_PATTERN = re.compile(r"\b(?:\+?91[- ]?)?[6-9]\d{9}\b")


def redact_pii(text: str) -> str:
    redacted = CARD_LIKE_PATTERN.sub("[REDACTED_CARD]", text)
    redacted = PHONE_LIKE_PATTERN.sub("[REDACTED_PHONE]", redacted)
    redacted = OTP_LIKE_PATTERN.sub("[REDACTED_CODE]", redacted)
    return redacted
