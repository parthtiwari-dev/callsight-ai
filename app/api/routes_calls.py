from fastapi import APIRouter

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls() -> dict[str, list]:
    return {"calls": []}


@router.get("/{call_id}")
def get_call(call_id: str) -> dict[str, str]:
    return {"call_id": call_id, "status": "not_loaded_in_phase_1"}
