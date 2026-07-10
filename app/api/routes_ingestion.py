from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import DbSession
from app.api.schemas import IngestResponse, MockIngestRequest
from app.db import crud
from app.ingestion.base import NormalizedCall
from app.pipeline.orchestrator import process_and_store_call

router = APIRouter(tags=["ingestion"])


def _normalized_from_request(payload: MockIngestRequest, audio_ref: str = "mock://fixture") -> NormalizedCall:
    return NormalizedCall(
        external_call_id=payload.external_call_id,
        advisor_ref=payload.advisor_ref,
        customer_ref_hashed=payload.customer_ref_hashed,
        audio_ref=audio_ref,
        started_at=payload.started_at,
        duration_seconds=payload.duration_seconds,
        metadata=payload.model_dump(mode="json"),
    )


@router.post("/webhooks/ingest/{source_type}", response_model=IngestResponse)
def ingest_webhook(
    source_type: str,
    payload: MockIngestRequest,
    db: DbSession,
) -> IngestResponse:
    if source_type != "generic_webhook":
        raise HTTPException(status_code=400, detail="Only generic_webhook is implemented in this phase")
    if not payload.mock:
        raise HTTPException(status_code=400, detail="Phase 4+5 API demo requires mock=true")

    result = process_and_store_call(
        db,
        _normalized_from_request(payload),
        mock=True,
        analyze=True,
        mock_analysis=payload.mock_analysis,
    )
    return IngestResponse(
        call_id=result["db"]["call_id"],
        created=result["db"]["created"],
        final_status=result["final_status"],
        analysis_summary=(result.get("analysis") or {}).get("summary"),
        active_flag_count=crud.count_active_flags(crud.get_call(db, UUID(result["db"]["call_id"]))),
    )


@router.post("/calls/upload", response_model=IngestResponse)
async def upload_call(
    db: DbSession,
    external_call_id: str = Form("mock-upload-call-001"),
    advisor_ref: str = Form("advisor-001"),
    customer_ref_hashed: str | None = Form("customer-demo-hash"),
    duration_seconds: int = Form(180),
    mock: bool = Form(True),
    mock_analysis: bool = Form(True),
    started_at: str | None = Form(None),
    audio: UploadFile | None = File(default=None),
) -> IngestResponse:
    started = datetime.fromisoformat(started_at) if started_at else None
    audio_ref = "mock://fixture"
    if audio is not None:
        upload_dir = Path("sample_calls/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / audio.filename
        destination.write_bytes(await audio.read())
        audio_ref = str(destination.resolve())
        mock = False

    payload = MockIngestRequest(
        external_call_id=external_call_id,
        advisor_ref=advisor_ref,
        customer_ref_hashed=customer_ref_hashed,
        started_at=started,
        duration_seconds=duration_seconds,
        mock=mock,
        mock_analysis=mock_analysis,
    )
    result = process_and_store_call(
        db,
        _normalized_from_request(payload, audio_ref),
        mock=mock,
        analyze=True,
        mock_analysis=mock_analysis,
    )
    return IngestResponse(
        call_id=result["db"]["call_id"],
        created=result["db"]["created"],
        final_status=result["final_status"],
        analysis_summary=(result.get("analysis") or {}).get("summary"),
        active_flag_count=crud.count_active_flags(crud.get_call(db, UUID(result["db"]["call_id"]))),
    )
