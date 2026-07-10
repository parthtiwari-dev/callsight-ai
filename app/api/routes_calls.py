from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.api.schemas import (
    CallAnalysisResponse,
    CallDetailResponse,
    CallListItem,
    IssueTagResponse,
    ScoreResponse,
    TranscriptSegmentResponse,
)
from app.db import crud
from app.db.models import Call, CallStatus, IssueTag

router = APIRouter(prefix="/calls", tags=["calls"])


def serialize_tag(tag: IssueTag) -> IssueTagResponse:
    return IssueTagResponse(
        tag_id=tag.tag_id,
        call_id=tag.call_id,
        segment_id=tag.segment_id,
        tag_type=tag.tag_type,
        severity=tag.severity,
        timestamp_in_call=tag.timestamp_in_call,
        quoted_line=tag.quoted_line,
        reason=tag.reason,
        confidence=tag.confidence,
        status=tag.status.value,
    )


def serialize_analysis(call: Call) -> CallAnalysisResponse | None:
    if call.analysis is None:
        return None
    return CallAnalysisResponse(
        call_id=call.call_id,
        summary=call.analysis.call_summary,
        scores=ScoreResponse(
            overall_score=call.analysis.overall_score,
            needs_discovery_score=call.analysis.needs_discovery_score,
            product_knowledge_score=call.analysis.product_knowledge_score,
            objection_handling_score=call.analysis.objection_handling_score,
            compliance_score=call.analysis.compliance_score,
            next_step_booking_score=call.analysis.next_step_booking_score,
        ),
        coaching_notes=call.analysis.coaching_notes,
        model_version=call.analysis.model_version,
        tags=[serialize_tag(tag) for tag in call.issue_tags],
    )


def serialize_call_list_item(call: Call) -> CallListItem:
    return CallListItem(
        call_id=call.call_id,
        external_call_id=call.external_call_id,
        advisor_id=call.advisor_id,
        advisor_name=call.advisor.name if call.advisor else None,
        team_id=call.advisor.team_id if call.advisor else None,
        status=call.status.value,
        started_at=call.started_at,
        duration_seconds=call.duration_seconds,
        overall_score=call.analysis.overall_score if call.analysis else None,
        active_flag_count=crud.count_active_flags(call),
    )


def serialize_call_detail(call: Call) -> CallDetailResponse:
    base = serialize_call_list_item(call).model_dump()
    return CallDetailResponse(
        **base,
        customer_ref_hashed=call.customer_ref_hashed,
        source_id=call.source_id,
        diarization_quality=call.diarization_quality,
        raw_audio_path=call.raw_audio_path,
        transcript=[
            TranscriptSegmentResponse(
                segment_id=segment.segment_id,
                speaker_label=segment.speaker_label,
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.text,
                language_code=segment.language_code,
            )
            for segment in sorted(call.transcript_segments, key=lambda item: item.start_time)
        ],
        analysis=serialize_analysis(call),
        tags=[serialize_tag(tag) for tag in call.issue_tags],
        contests=[
            {
                "contest_id": tag.contest.contest_id,
                "tag_id": tag.contest.tag_id,
                "advisor_id": tag.contest.advisor_id,
                "contest_reason": tag.contest.contest_reason,
                "status": tag.contest.status.value,
                "reviewed_by": tag.contest.reviewed_by,
                "created_at": tag.contest.created_at,
            }
            for tag in call.issue_tags
            if tag.contest is not None
        ],
    )


@router.get("", response_model=list[CallListItem])
def list_calls(
    db: DbSession,
    advisor_id: UUID | None = None,
    team_id: UUID | None = None,
    status: CallStatus | None = None,
    has_active_flags: bool | None = Query(default=None),
) -> list[CallListItem]:
    calls = crud.list_calls(
        db,
        advisor_id=advisor_id,
        team_id=team_id,
        status=status,
        has_active_flags=has_active_flags,
    )
    return [serialize_call_list_item(call) for call in calls]


@router.get("/{call_id}", response_model=CallDetailResponse)
def get_call(call_id: UUID, db: DbSession) -> CallDetailResponse:
    call = crud.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return serialize_call_detail(call)


@router.get("/{call_id}/transcript", response_model=list[TranscriptSegmentResponse])
def get_transcript(call_id: UUID, db: DbSession) -> list[TranscriptSegmentResponse]:
    call = crud.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return serialize_call_detail(call).transcript


@router.get("/{call_id}/analysis", response_model=CallAnalysisResponse)
def get_analysis(call_id: UUID, db: DbSession) -> CallAnalysisResponse:
    call = crud.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    analysis = serialize_analysis(call)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/{call_id}/reprocess", response_model=CallDetailResponse)
def reprocess_call(call_id: UUID, db: DbSession) -> CallDetailResponse:
    call = crud.get_call(db, call_id)
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    # Phase 4+5 supports reliable mock reprocessing. Real audio keeps using the same
    # pipeline hooks once speech dependencies are configured.
    from app.ingestion.base import NormalizedCall
    from app.pipeline.orchestrator import process_and_store_call

    payload = NormalizedCall(
        external_call_id=call.external_call_id,
        advisor_ref=call.advisor.external_ref if call.advisor else "advisor-001",
        customer_ref_hashed=call.customer_ref_hashed,
        audio_ref=call.raw_audio_path or "mock://fixture",
        started_at=call.started_at,
        duration_seconds=call.duration_seconds or 180,
        metadata={},
    )
    process_and_store_call(
        db,
        payload,
        mock=(call.raw_audio_path or "").startswith("mock://"),
        analyze=True,
        mock_analysis=True,
    )
    refreshed = crud.get_call(db, call_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Call not found after reprocess")
    return serialize_call_detail(refreshed)
