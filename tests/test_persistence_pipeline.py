from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Call, CallAnalysis, IssueTag, Organization, TranscriptSegment
from app.db.session import Base
from app.ingestion.base import NormalizedCall
from app.pipeline.orchestrator import analyze_pipeline_result, process_and_store_call, run_pipeline_spine


def test_mock_pipeline_analyzes_when_metadata_duration_is_sales_length():
    result = run_pipeline_spine(mock=True)

    analyzed = analyze_pipeline_result(
        result,
        mock_analysis=True,
        duration_seconds=180,
    )

    assert analyzed["final_status"] == "scored"
    assert analyzed["analysis"]["summary"]
    assert analyzed["analysis"]["overall_score"] > 0
    assert analyzed["verified_issues"]


def test_process_and_store_call_is_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    call_payload = NormalizedCall(
        external_call_id="mock-call-001",
        advisor_ref="advisor-001",
        customer_ref_hashed="customer-demo-hash",
        audio_ref="mock://fixture",
        started_at=datetime.fromisoformat("2026-07-10T13:40:00+05:30"),
        duration_seconds=180,
        metadata={},
    )

    with Session(engine) as db:
        first = process_and_store_call(
            db,
            call_payload,
            mock=True,
            analyze=True,
            mock_analysis=True,
        )
        second = process_and_store_call(
            db,
            call_payload,
            mock=True,
            analyze=True,
            mock_analysis=True,
        )

        assert first["db"]["created"] is True
        assert second["db"]["created"] is False
        assert db.query(Organization).count() == 1
        assert db.query(Call).count() == 1
        assert db.query(TranscriptSegment).count() == 3
        assert db.query(CallAnalysis).count() == 1
        assert db.query(IssueTag).count() >= 1
