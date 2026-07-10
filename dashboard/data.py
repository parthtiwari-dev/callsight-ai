from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session, selectinload

from app.db import crud
from app.db.models import (
    Call,
    CallAnalysis,
    ContestStatus,
    FlagContest,
    IssueTag,
    Organization,
    TagStatus,
    Team,
    User,
    UserRole,
)
from app.db.session import SessionLocal
from app.db.session import create_all_tables
from app.ingestion.base import NormalizedCall
from app.pipeline.orchestrator import process_and_store_call


def get_session() -> Session:
    create_all_tables()
    return SessionLocal()


def list_teams(db: Session) -> list[Team]:
    return db.query(Team).order_by(Team.name).all()


def list_advisors(db: Session, team_id: UUID | None = None) -> list[User]:
    query = db.query(User).filter(User.role == UserRole.advisor)
    if team_id:
        query = query.filter(User.team_id == team_id)
    return query.order_by(User.name).all()


def list_recent_calls(db: Session, limit: int = 20, team_id: UUID | None = None) -> list[Call]:
    query = (
        db.query(Call)
        .options(
            selectinload(Call.advisor).selectinload(User.team),
            selectinload(Call.analysis),
            selectinload(Call.issue_tags),
        )
        .join(User, Call.advisor_id == User.user_id, isouter=True)
    )
    if team_id:
        query = query.filter(User.team_id == team_id)
    return query.order_by(Call.created_at.desc()).limit(limit).all()


def get_call(db: Session, call_id: UUID) -> Call | None:
    return (
        db.query(Call)
        .options(
            selectinload(Call.advisor).selectinload(User.team),
            selectinload(Call.analysis),
            selectinload(Call.issue_tags).selectinload(IssueTag.contest),
            selectinload(Call.transcript_segments),
        )
        .filter(Call.call_id == call_id)
        .first()
    )


def org_summary(db: Session) -> dict:
    return crud.org_summary(db)


def advisor_summary(db: Session, advisor_id: UUID) -> dict:
    calls = (
        db.query(Call)
        .filter(Call.advisor_id == advisor_id)
        .order_by(Call.created_at.desc())
        .all()
    )
    scores = [call.analysis.overall_score for call in calls if call.analysis]
    active_tags = [
        tag
        for call in calls
        for tag in call.issue_tags
        if tag.status in crud.ACTIVE_TAG_STATUSES
    ]
    resolved_contests = (
        db.query(FlagContest)
        .filter(
            FlagContest.advisor_id == advisor_id,
            FlagContest.status.in_([ContestStatus.upheld, ContestStatus.dismissed]),
        )
        .all()
    )
    return {
        "calls": calls,
        "average_score": round(sum(scores) / len(scores), 2) if scores else None,
        "active_tags": active_tags,
        "coaching_notes": [
            note
            for call in calls
            if call.analysis
            for note in call.analysis.coaching_notes
        ][:8],
        "resolved_contests": resolved_contests,
    }


def team_summary(db: Session, team_id: UUID) -> dict:
    team = db.get(Team, team_id)
    advisors = list_advisors(db, team_id)
    calls = list_recent_calls(db, 100, team_id)
    scored = [call.analysis.overall_score for call in calls if call.analysis]
    pending_contests = (
        db.query(FlagContest)
        .join(IssueTag, FlagContest.tag_id == IssueTag.tag_id)
        .join(Call, IssueTag.call_id == Call.call_id)
        .join(User, Call.advisor_id == User.user_id)
        .filter(User.team_id == team_id, FlagContest.status == ContestStatus.pending)
        .all()
    )
    tag_distribution: dict[str, int] = {}
    for call in calls:
        for tag in call.issue_tags:
            if tag.status in crud.ACTIVE_TAG_STATUSES:
                key = f"{tag.tag_type} / {tag.severity}"
                tag_distribution[key] = tag_distribution.get(key, 0) + 1
    advisor_rows = []
    for advisor in advisors:
        advisor_calls = [call for call in calls if call.advisor_id == advisor.user_id]
        advisor_scores = [call.analysis.overall_score for call in advisor_calls if call.analysis]
        advisor_rows.append(
            {
                "Advisor": advisor.name,
                "Calls": len(advisor_calls),
                "Avg score": round(sum(advisor_scores) / len(advisor_scores), 2)
                if advisor_scores
                else None,
                "Active flags": sum(
                    1
                    for call in advisor_calls
                    for tag in call.issue_tags
                    if tag.status in crud.ACTIVE_TAG_STATUSES
                ),
            }
        )
    return {
        "team": team,
        "calls": calls,
        "average_score": round(sum(scored) / len(scored), 2) if scored else None,
        "advisor_rows": advisor_rows,
        "tag_distribution": tag_distribution,
        "pending_contests": pending_contests,
    }


def contest_tag(db: Session, call_id: UUID, tag_id: UUID, advisor_id: UUID, reason: str):
    return crud.create_contest(
        db,
        call_id=call_id,
        tag_id=tag_id,
        advisor_id=advisor_id,
        contest_reason=reason,
    )


def resolve_tag(db: Session, tag_id: UUID, reviewed_by: UUID, resolution: str):
    return crud.resolve_contest(
        db,
        tag_id=tag_id,
        reviewed_by=reviewed_by,
        resolution=resolution,
    )


def process_dashboard_call(
    db: Session,
    *,
    external_call_id: str,
    advisor_ref: str,
    customer_ref_hashed: str | None,
    duration_seconds: int,
    started_at: datetime | None = None,
    audio_ref: str = "mock://fixture",
    mock: bool = True,
    mock_analysis: bool = True,
) -> dict:
    normalized = NormalizedCall(
        external_call_id=external_call_id,
        advisor_ref=advisor_ref,
        customer_ref_hashed=customer_ref_hashed,
        audio_ref=audio_ref,
        started_at=started_at,
        duration_seconds=duration_seconds,
        metadata={
            "external_call_id": external_call_id,
            "advisor_ref": advisor_ref,
            "customer_ref_hashed": customer_ref_hashed,
            "started_at": started_at.isoformat() if started_at else None,
            "duration_seconds": duration_seconds,
        },
    )
    result = process_and_store_call(
        db,
        normalized,
        mock=mock,
        analyze=True,
        mock_analysis=mock_analysis,
    )
    call = get_call(db, UUID(result["db"]["call_id"]))
    analysis = result.get("analysis") or {}
    return {
        "call_id": result["db"]["call_id"],
        "created": result["db"]["created"],
        "final_status": result["final_status"],
        "overall_score": analysis.get("overall_score"),
        "active_flag_count": crud.count_active_flags(call) if call else 0,
        "segment_count": len(call.transcript_segments) if call else 0,
    }
