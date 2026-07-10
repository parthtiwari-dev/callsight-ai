from app.ingestion.base import CallSource, NormalizedCall


class StubExotelSource(CallSource):
    def fetch_new_calls(self) -> list[NormalizedCall]:
        raise NotImplementedError(
            "Real Exotel integration would poll or receive Exotel call records, map "
            "their call SID, agent, recording URL, timestamp, and duration into "
            "NormalizedCall, then let the shared pipeline handle the rest."
        )

    def get_audio(self, audio_ref: str) -> bytes:
        raise NotImplementedError(
            "Real Exotel integration would download the recording URL using vendor "
            "auth and return bytes without changing downstream pipeline code."
        )
