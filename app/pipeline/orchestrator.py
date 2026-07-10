from dataclasses import asdict
from pathlib import Path

from app.pipeline.diarization import SpeakerTurn, diarize_audio, map_speaker_roles
from app.pipeline.overlap_detector import detect_overlaps
from app.pipeline.pii_redaction import redact_pii
from app.pipeline.transcription import (
    TranscriptSegmentDraft,
    mock_transcript_segments,
    transcribe_audio,
)


def assign_speakers_by_overlap(
    transcript_segments: list[TranscriptSegmentDraft], speaker_turns: list[SpeakerTurn]
) -> list[TranscriptSegmentDraft]:
    role_map = map_speaker_roles(speaker_turns)
    merged: list[TranscriptSegmentDraft] = []
    for segment in transcript_segments:
        best_turn: SpeakerTurn | None = None
        best_overlap = 0.0
        for turn in speaker_turns:
            overlap = min(segment.end_time, turn.end_time) - max(
                segment.start_time, turn.start_time
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_turn = turn
        speaker = role_map.get(best_turn.speaker, "unknown") if best_turn else "unknown"
        merged.append(
            TranscriptSegmentDraft(
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=redact_pii(segment.text),
                speaker_label=speaker,
                language_code=segment.language_code,
            )
        )
    return merged


def run_pipeline_spine(audio_path: str | Path | None = None, mock: bool = False) -> dict:
    if mock:
        segments = [
            TranscriptSegmentDraft(
                item.start_time,
                item.end_time,
                redact_pii(item.text),
                item.speaker_label,
                item.language_code,
            )
            for item in mock_transcript_segments()
        ]
        return {
            "mode": "mock",
            "diarization_quality": "mock",
            "segments": [asdict(segment) for segment in segments],
            "overlap_events": [],
        }

    if audio_path is None:
        raise ValueError("audio_path is required when mock=False")

    transcript = transcribe_audio(audio_path)
    speaker_turns = diarize_audio(audio_path)
    merged = assign_speakers_by_overlap(transcript, speaker_turns)
    overlaps = detect_overlaps(speaker_turns)
    return {
        "mode": "speech",
        "diarization_quality": "available" if speaker_turns else "low",
        "segments": [asdict(segment) for segment in merged],
        "overlap_events": [asdict(event) for event in overlaps],
    }
