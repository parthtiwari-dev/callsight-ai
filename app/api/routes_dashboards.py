from fastapi import APIRouter

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/org-summary")
def org_summary() -> dict[str, str]:
    return {"status": "dashboard_queries_land_in_later_phase"}
