from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["ingestion"])


@router.post("/ingest/{source_type}")
def ingest_webhook(source_type: str, payload: dict) -> dict:
    return {
        "status": "accepted",
        "source_type": source_type,
        "message": "Webhook payload accepted by Phase 1 skeleton.",
        "payload": payload,
    }
