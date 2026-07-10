from dataclasses import asdict
from pathlib import Path

from sqlalchemy.orm import Session

from app.analysis.analyzer import analyze_transcript
from app.analysis.guardrails import apply_analysis_guardrails
from app.analysis.non_sales_gate import is_likely_sales_call
from app.db import crud
from app.db.models import CallStatus
from app.ingestion.base import NormalizedCall
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


def transcript_text_from_segments(segments: list[TranscriptSegmentDraft]) -> str:
    return "\n".join(
        f"[{segment.start_time:.1f}-{segment.end_time:.1f}] {segment.speaker_label}: {segment.text}"
        for segment in segments
    )


def transcript_lines_from_segments(segments: list[TranscriptSegmentDraft]) -> list[str]:
    return [segment.text for segment in segments]


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


def _segments_from_pipeline_result(result: dict) -> list[TranscriptSegmentDraft]:
    return [
        TranscriptSegmentDraft(
            start_time=float(segment["start_time"]),
            end_time=float(segment["end_time"]),
            text=segment["text"],
            speaker_label=segment.get("speaker_label", "unknown"),
            language_code=segment.get("language_code"),
        )
        for segment in result["segments"]
    ]


def analyze_pipeline_result(
    result: dict,
    *,
    mock_analysis: bool = False,
    duration_seconds: int | None = None,
) -> dict:
    segments = _segments_from_pipeline_result(result)
    transcript_text = transcript_text_from_segments(segments)
    duration = duration_seconds or int(max((segment.end_time for segment in segments), default=0))

    if not is_likely_sales_call(transcript_text, duration):
        return {
            **result,
            "analysis": None,
            "verified_issues": [],
            "rejected_issues": [],
            "final_status": CallStatus.excluded_non_sales.value,
        }

    analysis = analyze_transcript(
        transcript_text,
        result.get("overlap_events", []),
        mock=mock_analysis,
    )
    guarded = apply_analysis_guardrails(analysis, transcript_lines_from_segments(segments))
    return {
        **result,
        "analysis": guarded.analysis.model_dump(mode="json"),
        "verified_issues": [issue.model_dump(mode="json") for issue in guarded.analysis.issues],
        "rejected_issues": [issue.model_dump(mode="json") for issue in guarded.rejected_issues],
        "final_status": (
            CallStatus.scored.value
            if guarded.analysis.is_sales_call
            else CallStatus.excluded_non_sales.value
        ),
    }


def process_and_store_call(
    db: Session,
    normalized_call: NormalizedCall,
    *,
    mock: bool = False,
    analyze: bool = True,
    mock_analysis: bool = False,
) -> dict:
    org = crud.get_or_create_demo_org(db)
    team = crud.get_or_create_demo_team(db, org.org_id)
    advisor = crud.get_or_create_advisor(
        db, org_id=org.org_id, team_id=team.team_id, advisor_ref=normalized_call.advisor_ref
    )
    source = crud.get_or_create_call_source(db, org.org_id, "mock" if mock else "folder")
    call, created = crud.create_call_if_new(
        db,
        org_id=org.org_id,
        advisor_id=advisor.user_id,
        source_id=source.source_id,
        external_call_id=normalized_call.external_call_id,
        customer_ref_hashed=normalized_call.customer_ref_hashed,
        started_at=normalized_call.started_at,
        duration_seconds=normalized_call.duration_seconds,
        raw_audio_path=normalized_call.audio_ref,
    )
    crud.add_processing_event(
        db,
        call_id=call.call_id,
        stage="ingestion",
        status="created" if created else "reused",
    )

    try:
        crud.update_call_status(db, call, CallStatus.transcribing)
        result = run_pipeline_spine(normalized_call.audio_ref, mock=mock)
        segments = _segments_from_pipeline_result(result)
        stored_segments = crud.replace_transcript_segments(db, call, segments)
        crud.update_call_status(
            db,
            call,
            CallStatus.analyzing if analyze else CallStatus.ingested,
            diarization_quality=result.get("diarization_quality"),
        )

        if analyze:
            result = analyze_pipeline_result(
                result,
                mock_analysis=mock_analysis,
                duration_seconds=normalized_call.duration_seconds,
            )
            if result["analysis"] is None:
                crud.update_call_status(db, call, CallStatus.excluded_non_sales)
            else:
                from app.analysis.schemas import AnalysisOutput

                analysis = AnalysisOutput.model_validate(result["analysis"])
                crud.upsert_call_analysis(db, call, analysis)
                crud.replace_issue_tags(db, call, analysis.issues, stored_segments)
                for rejected in result["rejected_issues"]:
                    crud.add_processing_event(
                        db,
                        call_id=call.call_id,
                        stage="guardrails",
                        status="rejected_hallucinated_tag",
                        error_message=str(rejected),
                    )
                crud.update_call_status(db, call, CallStatus.scored)

        return {
            **result,
            "db": {
                "org_id": str(org.org_id),
                "team_id": str(team.team_id),
                "advisor_id": str(advisor.user_id),
                "source_id": str(source.source_id),
                "call_id": str(call.call_id),
                "created": created,
            },
        }
    except Exception as exc:
        db.rollback()
        crud.add_processing_event(
            db,
            call_id=call.call_id,
            stage="pipeline",
            status="failed",
            error_message=str(exc),
        )
        crud.update_call_status(db, call, CallStatus.failed)
        raise
