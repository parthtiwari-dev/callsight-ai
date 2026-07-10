from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpeakerTurn:
    start_time: float
    end_time: float
    speaker: str
    confidence: float | None = None


def diarize_audio(audio_path: str | Path) -> list[SpeakerTurn]:
    from app.config import get_settings

    settings = get_settings()
    if not settings.huggingface_access_token:
        raise RuntimeError(
            "HUGGINGFACE_ACCESS_TOKEN is required for pyannote diarization. "
            "Use `--mock` until model access is ready."
        )

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "pyannote.audio is not installed. Run `pip install -r requirements-speech.txt` "
            "or use `--mock`."
        ) from exc

    pipeline = Pipeline.from_pretrained(
        settings.diarization_model,
        token=settings.huggingface_access_token,
    )
    output = pipeline(str(audio_path))
    return [
        SpeakerTurn(float(turn.start), float(turn.end), str(speaker))
        for turn, _, speaker in output.itertracks(yield_label=True)
    ]


def map_speaker_roles(turns: list[SpeakerTurn]) -> dict[str, str]:
    if not turns:
        return {}
    first_speaker = sorted(turns, key=lambda turn: turn.start_time)[0].speaker
    return {
        speaker: ("advisor" if speaker == first_speaker else "customer")
        for speaker in {turn.speaker for turn in turns}
    }
