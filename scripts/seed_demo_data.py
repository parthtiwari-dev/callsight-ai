import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from app.analysis.schemas import AnalysisOutput, IssueTagOutput, ScoreDimension, Scores
from app.db import crud
from app.db.models import Call, FlagContest, IssueTag, Team, TranscriptSegment, User
from app.db.session import SessionLocal, create_all_tables
from app.ingestion.base import NormalizedCall
from app.pipeline.orchestrator import process_and_store_call


TEAMS = {
    "North Growth": ["asha-north", "rohan-north", "meera-north"],
    "South Growth": ["dev-south", "tara-south", "kabir-south"],
    "Renewals": ["neha-renewals", "arjun-renewals"],
}

TAG_PLAN = [
    ("price_before_value", "medium", 0.74),
    ("no_needs_discovery", "high", 0.81),
    ("weak_or_missing_trial_booking", "medium", 0.69),
    ("pressure_or_urgency", "high", 0.77),
    ("over_promising", "critical", 0.92),
]


def clear_seed_calls(db: Session) -> None:
    seed_calls = db.query(Call).filter(Call.external_call_id.like("seed-call-%")).all()
    call_ids = [call.call_id for call in seed_calls]
    if not call_ids:
        return
    tag_ids = [
        tag.tag_id
        for tag in db.query(IssueTag).filter(IssueTag.call_id.in_(call_ids)).all()
    ]
    if tag_ids:
        db.query(FlagContest).filter(FlagContest.tag_id.in_(tag_ids)).delete(
            synchronize_session=False
        )
    db.query(IssueTag).filter(IssueTag.call_id.in_(call_ids)).delete(
        synchronize_session=False
    )
    db.query(TranscriptSegment).filter(TranscriptSegment.call_id.in_(call_ids)).delete(
        synchronize_session=False
    )
    for call in seed_calls:
        if call.analysis:
            db.delete(call.analysis)
        db.delete(call)
    db.commit()


def score_dimension(score: float, name: str) -> ScoreDimension:
    return ScoreDimension(score=score, rationale=f"Seeded demo rationale for {name}.")


def build_analysis(call_index: int, tag_type: str, severity: str, confidence: float) -> AnalysisOutput:
    base = 8.2 - (call_index % 5) * 0.45
    compliance = 9.0 if severity != "critical" else 3.0
    issue = IssueTagOutput(
        tag_type=tag_type,
        severity=severity,
        timestamp=4.4,
        quoted_line="Yes, I want to lose weight but I am not sure about the cost.",
        reason=f"Seeded {tag_type.replace('_', ' ')} issue for dashboard demonstration.",
        confidence=confidence,
    )
    return AnalysisOutput(
        is_sales_call=True,
        summary=(
            "The advisor discussed FitNova goals, handled a pricing concern, "
            "and attempted to move the customer toward a trial session."
        ),
        scores=Scores(
            needs_discovery=score_dimension(max(base - 0.8, 3.0), "needs discovery"),
            product_knowledge=score_dimension(max(base - 0.2, 3.0), "product knowledge"),
            objection_handling=score_dimension(max(base - 0.4, 3.0), "objection handling"),
            compliance=score_dimension(compliance, "compliance"),
            next_step_booking=score_dimension(max(base - 0.6, 3.0), "next step booking"),
        ),
        issues=[issue],
        coaching=[
            "Ask one more discovery question before presenting the plan.",
            "Tie price back to the customer's stated goal before closing.",
        ],
        model_version="seeded-demo-v1",
    )


def seed_demo_data(db: Session) -> dict:
    clear_seed_calls(db)
    org = crud.get_or_create_demo_org(db)
    source = crud.get_or_create_call_source(db, org.org_id, "mock")

    advisors: list[User] = []
    for team_name, advisor_refs in TEAMS.items():
        team = db.query(Team).filter(Team.org_id == org.org_id, Team.name == team_name).first()
        if team is None:
            team = crud.create_team(db, org.org_id, team_name)
        for advisor_ref in advisor_refs:
            advisors.append(
                crud.get_or_create_advisor(
                    db,
                    org_id=org.org_id,
                    team_id=team.team_id,
                    advisor_ref=advisor_ref,
                )
            )

    created_calls = []
    now = datetime.now(timezone.utc)
    for index in range(16):
        advisor = advisors[index % len(advisors)]
        external_id = f"seed-call-{index + 1:03d}"
        payload = NormalizedCall(
            external_call_id=external_id,
            advisor_ref=advisor.external_ref or f"advisor-{index}",
            customer_ref_hashed=f"seed-customer-{index + 1:03d}",
            audio_ref="mock://fixture",
            started_at=now - timedelta(days=index),
            duration_seconds=180 + index * 12,
            metadata={},
        )
        result = process_and_store_call(
            db,
            payload,
            mock=True,
            analyze=True,
            mock_analysis=True,
        )
        call = crud.get_call(db, UUID(result["db"]["call_id"]))
        tag_type, severity, confidence = TAG_PLAN[index % len(TAG_PLAN)]
        analysis = build_analysis(index, tag_type, severity, confidence)
        crud.upsert_call_analysis(db, call, analysis)
        stored_segments = (
            db.query(TranscriptSegment)
            .filter(TranscriptSegment.call_id == call.call_id)
            .order_by(TranscriptSegment.start_time)
            .all()
        )
        tags = crud.replace_issue_tags(db, call, analysis.issues, stored_segments)
        created_calls.append(call)

        if index in {1, 5, 9} and tags:
            contest, tag = crud.create_contest(
                db,
                call_id=call.call_id,
                tag_id=tags[0].tag_id,
                advisor_id=advisor.user_id,
                contest_reason="Seeded advisor dispute for review workflow.",
            )
            if index == 5:
                crud.resolve_contest(
                    db,
                    tag_id=tag.tag_id,
                    reviewed_by=advisor.user_id,
                    resolution="dismissed",
                )
            elif index == 9:
                crud.resolve_contest(
                    db,
                    tag_id=tag.tag_id,
                    reviewed_by=advisor.user_id,
                    resolution="upheld",
                )

    db.commit()
    empty_demo_team = (
        db.query(Team)
        .filter(Team.org_id == org.org_id, Team.name == "Demo Sales Team")
        .first()
    )
    if empty_demo_team and not empty_demo_team.users:
        db.delete(empty_demo_team)
        db.commit()
    return {
        "org_id": str(org.org_id),
        "teams": len(TEAMS),
        "advisors": len(advisors),
        "calls": len(created_calls),
    }


def main() -> int:
    create_all_tables()
    with SessionLocal() as db:
        result = seed_demo_data(db)
    print(
        "Seeded FitNova demo data: "
        f"{result['teams']} teams, {result['advisors']} advisors, {result['calls']} calls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
