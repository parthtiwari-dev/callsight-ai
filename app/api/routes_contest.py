from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.api.routes_calls import serialize_tag
from app.api.schemas import ContestActionResponse, ContestRequest, ContestResolutionRequest, ContestResponse
from app.db import crud

router = APIRouter(tags=["contests"])


def serialize_contest_action(contest, tag) -> ContestActionResponse:
    return ContestActionResponse(
        contest=ContestResponse(
            contest_id=contest.contest_id,
            tag_id=contest.tag_id,
            advisor_id=contest.advisor_id,
            contest_reason=contest.contest_reason,
            status=contest.status.value,
            reviewed_by=contest.reviewed_by,
            created_at=contest.created_at,
        ),
        tag=serialize_tag(tag),
    )


@router.post(
    "/calls/{call_id}/tags/{tag_id}/contest",
    response_model=ContestActionResponse,
)
def contest_tag(
    call_id: UUID,
    tag_id: UUID,
    payload: ContestRequest,
    db: DbSession,
) -> ContestActionResponse:
    try:
        contest, tag = crud.create_contest(
            db,
            call_id=call_id,
            tag_id=tag_id,
            advisor_id=payload.advisor_id,
            contest_reason=payload.contest_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_contest_action(contest, tag)


@router.post("/admin/tags/{tag_id}/resolve", response_model=ContestActionResponse)
def resolve_tag(
    tag_id: UUID,
    payload: ContestResolutionRequest,
    db: DbSession,
) -> ContestActionResponse:
    try:
        contest, tag = crud.resolve_contest(
            db,
            tag_id=tag_id,
            reviewed_by=payload.reviewed_by,
            resolution=payload.resolution,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_contest_action(contest, tag)
