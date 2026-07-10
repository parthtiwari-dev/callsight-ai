from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analysis.non_sales_gate import is_likely_sales_call
from app.db import crud
from app.db.models import IssueTag, TagStatus
from app.db.session import Base
from app.pipeline.pii_redaction import redact_pii
from dashboard import data
from scripts.seed_demo_data import seed_demo_data


def test_seed_demo_data_populates_dashboard_helpers():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        result = seed_demo_data(db)
        summary = data.org_summary(db)
        teams = data.list_teams(db)
        advisors = data.list_advisors(db)

        assert result["calls"] == 16
        assert len(teams) == 3
        assert len(advisors) == 8
        assert summary["calls_processed"] == 16
        assert summary["average_overall_score"] is not None
        assert summary["top_issue_tags"]


def test_dismissed_tags_are_excluded_from_rollups():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        seed_demo_data(db)
        active_before = len(crud.org_summary(db)["top_issue_tags"])
        tag = db.query(IssueTag).filter(IssueTag.status != TagStatus.dismissed).first()
        tag.status = TagStatus.dismissed
        db.commit()

        summary = crud.org_summary(db)

        assert active_before > 0
        assert all(item["count"] > 0 for item in summary["top_issue_tags"])
        assert tag.status == TagStatus.dismissed


def test_non_sales_gate_excludes_short_wrong_number_style_call():
    assert is_likely_sales_call("wrong number, sorry", 8) is False


def test_pii_redaction_masks_phone_card_and_otp_like_values():
    text = "Call me at 9876543210, card 4111 1111 1111 1111, OTP 123456."

    redacted = redact_pii(text)

    assert "9876543210" not in redacted
    assert "4111 1111 1111 1111" not in redacted
    assert "123456" not in redacted
