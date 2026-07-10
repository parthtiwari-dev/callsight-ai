from datetime import datetime

from pydantic import BaseModel, Field

from app.ingestion.base import CallSource, NormalizedCall


class GenericWebhookPayload(BaseModel):
    external_call_id: str
    advisor_ref: str
    customer_ref_hashed: str | None = None
    audio_ref: str
    started_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class GenericWebhookSource(CallSource):
    def __init__(self, payloads: list[GenericWebhookPayload] | None = None):
        self.payloads = payloads or []

    def fetch_new_calls(self) -> list[NormalizedCall]:
        return [
            NormalizedCall(
                external_call_id=payload.external_call_id,
                advisor_ref=payload.advisor_ref,
                customer_ref_hashed=payload.customer_ref_hashed,
                audio_ref=payload.audio_ref,
                started_at=payload.started_at,
                duration_seconds=payload.duration_seconds,
                metadata=payload.model_dump(mode="json"),
            )
            for payload in self.payloads
        ]

    def get_audio(self, audio_ref: str) -> bytes:
        raise NotImplementedError(
            "GenericWebhookSource stores a normalized audio_ref; configure a blob/file "
            "resolver before using it for audio bytes."
        )
