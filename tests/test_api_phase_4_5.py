from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.ingestion.base import NormalizedCall
from app.main import app
from app.pipeline.orchestrator import process_and_store_call


@pytest.fixture()
def client_and_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    with TestingSessionLocal() as db:
        yield client, db
    app.dependency_overrides.clear()


def seed_scored_call(db: Session) -> dict:
    payload = NormalizedCall(
        external_call_id="api-call-001",
        advisor_ref="advisor-001",
        customer_ref_hashed="customer-demo-hash",
        audio_ref="mock://fixture",
        started_at=None,
        duration_seconds=180,
        metadata={},
    )
    return process_and_store_call(
        db,
        payload,
        mock=True,
        analyze=True,
        mock_analysis=True,
    )


def test_calls_transcript_and_analysis_endpoints(client_and_db):
    client, db = client_and_db
    seeded = seed_scored_call(db)
    call_id = seeded["db"]["call_id"]

    calls = client.get("/calls").json()
    assert len(calls) == 1
    assert calls[0]["call_id"] == call_id
    assert calls[0]["active_flag_count"] == 1

    detail = client.get(f"/calls/{call_id}").json()
    assert detail["analysis"]["summary"]
    assert len(detail["transcript"]) == 3
    assert len(detail["tags"]) == 1

    transcript = client.get(f"/calls/{call_id}/transcript").json()
    assert len(transcript) == 3

    analysis = client.get(f"/calls/{call_id}/analysis").json()
    assert analysis["scores"]["overall_score"] == 7.33
    assert analysis["tags"][0]["tag_type"] == "price_before_value"


def test_contest_and_resolve_updates_dashboard_rollups(client_and_db):
    client, db = client_and_db
    seeded = seed_scored_call(db)
    call_id = seeded["db"]["call_id"]
    advisor_id = seeded["db"]["advisor_id"]
    tag_id = client.get(f"/calls/{call_id}/analysis").json()["tags"][0]["tag_id"]

    contested = client.post(
        f"/calls/{call_id}/tags/{tag_id}/contest",
        json={"advisor_id": advisor_id, "contest_reason": "Customer raised price first."},
    )
    assert contested.status_code == 200
    assert contested.json()["contest"]["status"] == "pending"
    assert contested.json()["tag"]["status"] == "contested"

    dismissed = client.post(
        f"/admin/tags/{tag_id}/resolve",
        json={"reviewed_by": advisor_id, "resolution": "dismissed"},
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["contest"]["status"] == "dismissed"
    assert dismissed.json()["tag"]["status"] == "dismissed"

    summary = client.get("/dashboards/org-summary").json()
    assert summary["calls_processed"] == 1
    assert summary["top_issue_tags"] == []


def test_webhook_and_upload_mock_ingest(client_and_db):
    client, _ = client_and_db

    webhook = client.post(
        "/webhooks/ingest/generic_webhook",
        json={
            "external_call_id": "api-webhook-001",
            "advisor_ref": "advisor-001",
            "customer_ref_hashed": "customer-demo-hash",
            "duration_seconds": 180,
            "mock": True,
            "mock_analysis": True,
        },
    )
    assert webhook.status_code == 200
    assert webhook.json()["final_status"] == "scored"

    upload = client.post(
        "/calls/upload",
        data={
            "external_call_id": "api-upload-001",
            "advisor_ref": "advisor-001",
            "duration_seconds": "180",
            "mock": "true",
            "mock_analysis": "true",
        },
    )
    assert upload.status_code == 200
    assert upload.json()["final_status"] == "scored"

    calls = client.get("/calls").json()
    assert len(calls) == 2
