from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.api.routes_calls import serialize_call_list_item, serialize_tag
from app.api.schemas import DashboardSummaryResponse
from app.db import crud
from app.db.models import Call, CallAnalysis, FlagContest, IssueTag, TagStatus, Team, User

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/org-summary", response_model=DashboardSummaryResponse)
def org_summary(db: DbSession) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(**crud.org_summary(db))


@router.get("/team-summary/{team_id}")
def team_summary(team_id: UUID, db: DbSession) -> dict:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    calls = (
        db.query(Call)
        .join(User, Call.advisor_id == User.user_id)
        .filter(User.team_id == team_id)
        .all()
    )
    scored = [call.analysis.overall_score for call in calls if call.analysis]
    advisors = db.query(User).filter(User.team_id == team_id).all()
    advisor_rows = []
    for advisor in advisors:
        advisor_scores = [
            call.analysis.overall_score
            for call in calls
            if call.advisor_id == advisor.user_id and call.analysis
        ]
        advisor_rows.append(
            {
                "advisor_id": str(advisor.user_id),
                "advisor_name": advisor.name,
                "average_overall_score": round(sum(advisor_scores) / len(advisor_scores), 2)
                if advisor_scores
                else None,
                "calls_processed": len(advisor_scores),
            }
        )

    active_tags = (
        db.query(IssueTag)
        .join(Call, IssueTag.call_id == Call.call_id)
        .join(User, Call.advisor_id == User.user_id)
        .filter(User.team_id == team_id, IssueTag.status.in_(list(crud.ACTIVE_TAG_STATUSES)))
        .all()
    )
    tag_distribution: dict[str, int] = {}
    for tag in active_tags:
        key = f"{tag.tag_type}:{tag.severity}"
        tag_distribution[key] = tag_distribution.get(key, 0) + 1

    pending_contests = (
        db.query(FlagContest)
        .join(IssueTag, FlagContest.tag_id == IssueTag.tag_id)
        .join(Call, IssueTag.call_id == Call.call_id)
        .join(User, Call.advisor_id == User.user_id)
        .filter(User.team_id == team_id, FlagContest.status == "pending")
        .count()
    )
    return {
        "team_id": str(team.team_id),
        "team_name": team.name,
        "average_overall_score": round(sum(scored) / len(scored), 2) if scored else None,
        "per_advisor": advisor_rows,
        "active_tag_distribution": tag_distribution,
        "pending_contest_count": pending_contests,
    }


@router.get("/advisor-summary/{advisor_id}")
def advisor_summary(advisor_id: UUID, db: DbSession) -> dict:
    advisor = db.get(User, advisor_id)
    if advisor is None:
        raise HTTPException(status_code=404, detail="Advisor not found")
    calls = (
        db.query(Call)
        .filter(Call.advisor_id == advisor_id)
        .order_by(Call.created_at.desc())
        .all()
    )
    scores = [call.analysis.overall_score for call in calls if call.analysis]
    active_flags = [
        serialize_tag(tag).model_dump(mode="json")
        for call in calls
        for tag in call.issue_tags
        if tag.status in crud.ACTIVE_TAG_STATUSES
    ]
    coaching_notes = [
        note
        for call in calls
        if call.analysis
        for note in call.analysis.coaching_notes
    ][:10]
    resolved_contests = (
        db.query(FlagContest)
        .filter(
            FlagContest.advisor_id == advisor_id,
            FlagContest.status.in_(["upheld", "dismissed"]),
        )
        .all()
    )
    return {
        "advisor_id": str(advisor.user_id),
        "advisor_name": advisor.name,
        "average_overall_score": round(sum(scores) / len(scores), 2) if scores else None,
        "recent_calls": [serialize_call_list_item(call).model_dump(mode="json") for call in calls[:10]],
        "active_flags": active_flags,
        "coaching_notes": coaching_notes,
        "resolved_contest_history": [
            {
                "contest_id": str(contest.contest_id),
                "tag_id": str(contest.tag_id),
                "status": contest.status.value,
                "reviewed_by": str(contest.reviewed_by) if contest.reviewed_by else None,
            }
            for contest in resolved_contests
        ],
    }
