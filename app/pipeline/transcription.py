from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptSegmentDraft:
    start_time: float
    end_time: float
    text: str
    speaker_label: str = "unknown"
    language_code: str | None = None


def mock_transcript_segments() -> list[TranscriptSegmentDraft]:
    return [
        TranscriptSegmentDraft(
            0.0,
            4.2,
            "Hi, this is Asha from FitNova. Are you looking for a fitness plan?",
            "advisor",
            "en",
        ),
        TranscriptSegmentDraft(
            4.4,
            8.0,
            "Yes, I want to lose weight but I am not sure about the cost.",
            "customer",
            "en",
        ),
        TranscriptSegmentDraft(
            8.3,
            14.0,
            "We can start with a trial session next Tuesday and discuss a plan.",
            "advisor",
            "en",
        ),
    ]


def transcribe_audio(audio_path: str | Path) -> list[TranscriptSegmentDraft]:
    from app.config import get_settings

    settings = get_settings()
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Run `pip install -r requirements-speech.txt` "
            "or use `--mock`."
        ) from exc

    model = WhisperModel(
        settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    segments, info = model.transcribe(str(audio_path), beam_size=5)
    language = getattr(info, "language", None)
    return [
        TranscriptSegmentDraft(
            start_time=float(segment.start),
            end_time=float(segment.end),
            text=segment.text.strip(),
            language_code=language,
        )
        for segment in segments
    ]
