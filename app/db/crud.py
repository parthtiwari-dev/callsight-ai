from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analysis.schemas import AnalysisOutput, IssueTagOutput
from app.db.models import (
    Call,
    CallAnalysis,
    CallSourceConfig,
    CallStatus,
    ContestStatus,
    FlagContest,
    IssueTag,
    Organization,
    ProcessingEvent,
    TagStatus,
    Team,
    TranscriptSegment,
    User,
    UserRole,
)
from app.pipeline.transcription import TranscriptSegmentDraft


def get_or_create_demo_org(db: Session, name: str = "FitNova") -> Organization:
    org = db.query(Organization).filter(Organization.name == name).first()
    if org:
        return org

    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def get_or_create_demo_team(
    db: Session, org_id: UUID, name: str = "Demo Sales Team"
) -> Team:
    team = db.query(Team).filter(Team.org_id == org_id, Team.name == name).first()
    if team:
        return team

    team = Team(org_id=org_id, name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def get_or_create_advisor(
    db: Session, *, org_id: UUID, team_id: UUID, advisor_ref: str
) -> User:
    advisor = (
        db.query(User)
        .filter(
            User.org_id == org_id,
            User.external_ref == advisor_ref,
            User.role == UserRole.advisor,
        )
        .first()
    )
    if advisor:
        return advisor

    advisor = User(
        org_id=org_id,
        team_id=team_id,
        external_ref=advisor_ref,
        name=advisor_ref.replace("-", " ").title(),
        role=UserRole.advisor,
    )
    db.add(advisor)
    db.commit()
    db.refresh(advisor)
    return advisor


def create_org(db: Session, name: str) -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def create_team(db: Session, org_id: UUID, name: str) -> Team:
    team = Team(org_id=org_id, name=name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def create_advisor(
    db: Session, *, org_id: UUID, team_id: UUID, name: str, external_ref: str | None = None
) -> User:
    advisor = User(
        org_id=org_id,
        team_id=team_id,
        external_ref=external_ref,
        name=name,
        role=UserRole.advisor,
    )
    db.add(advisor)
    db.commit()
    db.refresh(advisor)
    return advisor


def get_or_create_call_source(
    db: Session, org_id: UUID, adapter_type: str, config: dict | None = None
) -> CallSourceConfig:
    source = (
        db.query(CallSourceConfig)
        .filter(
            CallSourceConfig.org_id == org_id,
            CallSourceConfig.adapter_type == adapter_type,
            CallSourceConfig.active.is_(True),
        )
        .first()
    )
    if source:
        return source

    source = CallSourceConfig(org_id=org_id, adapter_type=adapter_type, config=config or {})
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def create_call_if_new(
    db: Session,
    *,
    org_id: UUID,
    source_id: UUID,
    external_call_id: str,
    advisor_id: UUID | None = None,
    customer_ref_hashed: str | None = None,
    started_at: datetime | None = None,
    duration_seconds: int | None = None,
    raw_audio_path: str | None = None,
) -> tuple[Call, bool]:
    call = Call(
        org_id=org_id,
        source_id=source_id,
        advisor_id=advisor_id,
        external_call_id=external_call_id,
        customer_ref_hashed=customer_ref_hashed,
        status=CallStatus.ingested,
        started_at=started_at,
        duration_seconds=duration_seconds,
        raw_audio_path=raw_audio_path,
    )
    db.add(call)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Call)
            .filter(Call.source_id == source_id, Call.external_call_id == external_call_id)
            .one()
        )
        return existing, False

    db.refresh(call)
    return call, True


def update_call_status(
    db: Session,
    call: Call,
    status: CallStatus,
    *,
    diarization_quality: str | None = None,
) -> Call:
    call.status = status
    if diarization_quality is not None:
        call.diarization_quality = diarization_quality
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def replace_transcript_segments(
    db: Session, call: Call, segments: list[TranscriptSegmentDraft]
) -> list[TranscriptSegment]:
    db.query(IssueTag).filter(IssueTag.call_id == call.call_id).delete()
    db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call.call_id).delete()
    rows = [
        TranscriptSegment(
            call_id=call.call_id,
            speaker_label=segment.speaker_label,
            start_time=segment.start_time,
            end_time=segment.end_time,
            text=segment.text,
            language_code=segment.language_code,
        )
        for segment in segments
    ]
    db.add_all(rows)
    db.commit()
    return (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.call_id == call.call_id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )


def upsert_call_analysis(db: Session, call: Call, analysis: AnalysisOutput) -> CallAnalysis:
    existing = db.get(CallAnalysis, call.call_id)
    if existing:
        db.delete(existing)
        db.flush()

    row = CallAnalysis(
        call_id=call.call_id,
        call_summary=analysis.summary,
        overall_score=analysis.overall_score or analysis.scores.weighted_overall(),
        needs_discovery_score=analysis.scores.needs_discovery.score,
        product_knowledge_score=analysis.scores.product_knowledge.score,
        objection_handling_score=analysis.scores.objection_handling.score,
        compliance_score=analysis.scores.compliance.score,
        next_step_booking_score=analysis.scores.next_step_booking.score,
        coaching_notes=analysis.coaching,
        model_version=analysis.model_version,
        raw_model_response=analysis.model_dump(mode="json"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _find_segment_for_issue(
    transcript_segments: list[TranscriptSegment], issue: IssueTagOutput
) -> TranscriptSegment | None:
    if issue.timestamp is not None:
        for segment in transcript_segments:
            if segment.start_time <= issue.timestamp <= segment.end_time:
                return segment
    for segment in transcript_segments:
        if issue.quoted_line and issue.quoted_line.lower() in segment.text.lower():
            return segment
    return None


def replace_issue_tags(
    db: Session,
    call: Call,
    issues: list[IssueTagOutput],
    transcript_segments: list[TranscriptSegment],
) -> list[IssueTag]:
    db.query(IssueTag).filter(IssueTag.call_id == call.call_id).delete()
    rows = []
    for issue in issues:
        segment = _find_segment_for_issue(transcript_segments, issue)
        rows.append(
            IssueTag(
                call_id=call.call_id,
                segment_id=segment.segment_id if segment else None,
                tag_type=issue.tag_type.value,
                severity=issue.severity.value,
                timestamp_in_call=issue.timestamp,
                quoted_line=issue.quoted_line,
                reason=issue.reason,
                confidence=issue.confidence,
                status=TagStatus.active,
            )
        )
    db.add_all(rows)
    db.commit()
    return (
        db.query(IssueTag)
        .filter(IssueTag.call_id == call.call_id)
        .order_by(IssueTag.timestamp_in_call)
        .all()
    )


def add_processing_event(
    db: Session,
    *,
    call_id: UUID | None,
    stage: str,
    status: str,
    error_message: str | None = None,
    retry_count: int = 0,
) -> ProcessingEvent:
    event = ProcessingEvent(
        call_id=call_id,
        stage=stage,
        status=status,
        error_message=error_message,
        retry_count=retry_count,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


ACTIVE_TAG_STATUSES = {TagStatus.active, TagStatus.contested, TagStatus.upheld}


def list_calls(
    db: Session,
    *,
    advisor_id: UUID | None = None,
    team_id: UUID | None = None,
    status: CallStatus | None = None,
    has_active_flags: bool | None = None,
) -> list[Call]:
    query = db.query(Call).outerjoin(User, Call.advisor_id == User.user_id)
    if advisor_id:
        query = query.filter(Call.advisor_id == advisor_id)
    if team_id:
        query = query.filter(User.team_id == team_id)
    if status:
        query = query.filter(Call.status == status)
    calls = query.order_by(Call.created_at.desc()).all()
    if has_active_flags is None:
        return calls
    filtered = []
    for call in calls:
        active_count = count_active_flags(call)
        if (has_active_flags and active_count > 0) or (
            not has_active_flags and active_count == 0
        ):
            filtered.append(call)
    return filtered


def get_call(db: Session, call_id: UUID) -> Call | None:
    return db.get(Call, call_id)


def count_active_flags(call: Call) -> int:
    return sum(1 for tag in call.issue_tags if tag.status in ACTIVE_TAG_STATUSES)


def create_contest(
    db: Session, *, call_id: UUID, tag_id: UUID, advisor_id: UUID, contest_reason: str
) -> tuple[FlagContest, IssueTag]:
    tag = db.get(IssueTag, tag_id)
    if tag is None or tag.call_id != call_id:
        raise ValueError("Tag does not belong to call.")
    if tag.status not in {TagStatus.active, TagStatus.contested}:
        raise ValueError("Only active or contested tags can be contested.")

    contest = tag.contest
    if contest is None:
        contest = FlagContest(
            tag_id=tag.tag_id,
            advisor_id=advisor_id,
            contest_reason=contest_reason,
            status=ContestStatus.pending,
        )
        db.add(contest)
    else:
        contest.advisor_id = advisor_id
        contest.contest_reason = contest_reason
        contest.status = ContestStatus.pending
        contest.reviewed_by = None
    tag.status = TagStatus.contested
    db.add(tag)
    db.commit()
    db.refresh(contest)
    db.refresh(tag)
    return contest, tag


def resolve_contest(
    db: Session, *, tag_id: UUID, reviewed_by: UUID, resolution: str
) -> tuple[FlagContest, IssueTag]:
    tag = db.get(IssueTag, tag_id)
    if tag is None:
        raise ValueError("Tag not found.")
    contest = tag.contest
    if contest is None:
        raise ValueError("Tag has no contest to resolve.")

    if resolution == "upheld":
        contest.status = ContestStatus.upheld
        tag.status = TagStatus.upheld
    elif resolution == "dismissed":
        contest.status = ContestStatus.dismissed
        tag.status = TagStatus.dismissed
    else:
        raise ValueError("Resolution must be upheld or dismissed.")

    contest.reviewed_by = reviewed_by
    db.add_all([contest, tag])
    db.commit()
    db.refresh(contest)
    db.refresh(tag)
    return contest, tag


def org_summary(db: Session) -> dict:
    analyses = db.query(CallAnalysis).all()
    calls_processed = db.query(Call).filter(Call.status == CallStatus.scored).count()
    average_score = (
        round(sum(item.overall_score for item in analyses) / len(analyses), 2)
        if analyses
        else None
    )
    active_tags = (
        db.query(IssueTag)
        .filter(IssueTag.status.in_(list(ACTIVE_TAG_STATUSES)))
        .all()
    )
    unresolved_critical = sum(
        1 for tag in active_tags if tag.severity == "critical"
    )
    tag_counts: dict[str, int] = {}
    for tag in active_tags:
        tag_counts[tag.tag_type] = tag_counts.get(tag.tag_type, 0) + 1

    team_rows = []
    for team in db.query(Team).all():
        team_calls = (
            db.query(Call)
            .join(User, Call.advisor_id == User.user_id)
            .join(CallAnalysis, Call.call_id == CallAnalysis.call_id)
            .filter(User.team_id == team.team_id)
            .all()
        )
        scores = [call.analysis.overall_score for call in team_calls if call.analysis]
        team_rows.append(
            {
                "team_id": str(team.team_id),
                "team_name": team.name,
                "average_overall_score": round(sum(scores) / len(scores), 2)
                if scores
                else None,
                "calls_processed": len(scores),
            }
        )

    return {
        "calls_processed": calls_processed,
        "average_overall_score": average_score,
        "unresolved_critical_flag_count": unresolved_critical,
        "top_issue_tags": [
            {"tag_type": tag_type, "count": count}
            for tag_type, count in sorted(
                tag_counts.items(), key=lambda item: item[1], reverse=True
            )
        ],
        "team_leaderboard": sorted(
            team_rows,
            key=lambda item: item["average_overall_score"] or 0,
            reverse=True,
        ),
    }
