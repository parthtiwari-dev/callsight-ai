from fastapi import APIRouter

router = APIRouter(tags=["contests"])


@router.post("/calls/{call_id}/tags/{tag_id}/contest")
def contest_tag(call_id: str, tag_id: str, payload: dict) -> dict:
    return {
        "call_id": call_id,
        "tag_id": tag_id,
        "status": "contest_endpoint_skeleton",
        "payload": payload,
    }
