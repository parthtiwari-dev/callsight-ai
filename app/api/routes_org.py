from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.api.schemas import (
    AdvisorCreateRequest,
    AdvisorResponse,
    OrgCreateRequest,
    OrgResponse,
    TeamCreateRequest,
    TeamResponse,
)
from app.db import crud
from app.db.models import Organization, Team

router = APIRouter(tags=["orgs"])


def serialize_org(org: Organization) -> OrgResponse:
    return OrgResponse(org_id=org.org_id, name=org.name)


def serialize_team(team: Team) -> TeamResponse:
    return TeamResponse(
        team_id=team.team_id,
        org_id=team.org_id,
        name=team.name,
        leader_user_id=team.leader_user_id,
    )


@router.get("/orgs", response_model=list[OrgResponse])
def list_orgs(db: DbSession) -> list[OrgResponse]:
    return [serialize_org(org) for org in db.query(Organization).order_by(Organization.name).all()]


@router.post("/orgs", response_model=OrgResponse)
def create_org(payload: OrgCreateRequest, db: DbSession) -> OrgResponse:
    return serialize_org(crud.create_org(db, payload.name))


@router.get("/orgs/{org_id}/teams", response_model=list[TeamResponse])
def list_teams(org_id: UUID, db: DbSession) -> list[TeamResponse]:
    return [
        serialize_team(team)
        for team in db.query(Team).filter(Team.org_id == org_id).order_by(Team.name).all()
    ]


@router.post("/orgs/{org_id}/teams", response_model=TeamResponse)
def create_team(org_id: UUID, payload: TeamCreateRequest, db: DbSession) -> TeamResponse:
    if db.get(Organization, org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return serialize_team(crud.create_team(db, org_id, payload.name))


@router.post("/teams/{team_id}/advisors", response_model=AdvisorResponse)
def create_advisor(
    team_id: UUID, payload: AdvisorCreateRequest, db: DbSession
) -> AdvisorResponse:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    advisor = crud.create_advisor(
        db,
        org_id=team.org_id,
        team_id=team.team_id,
        name=payload.name,
        external_ref=payload.external_ref,
    )
    return AdvisorResponse(
        user_id=advisor.user_id,
        org_id=advisor.org_id,
        team_id=advisor.team_id,
        external_ref=advisor.external_ref,
        name=advisor.name,
        role=advisor.role.value,
    )
