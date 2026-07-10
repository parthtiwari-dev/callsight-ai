from fastapi import APIRouter

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.get("")
def list_orgs() -> dict[str, list]:
    return {"orgs": []}
