from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Call, CallSourceConfig, CallStatus


def get_or_create_call_source(
    db: Session, org_id: UUID, adapter_type: str, config: dict | None = None
) -> CallSourceConfig:
    source = (
        db.query(CallSourceConfig)
        .filter(
            CallSourceConfig.org_id == org_id,
            CallSourceConfig.adapter_type == adapter_type,
            CallSourceConfig.active.is_(True),
        )
        .first()
    )
    if source:
        return source

    source = CallSourceConfig(org_id=org_id, adapter_type=adapter_type, config=config or {})
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def create_call_if_new(
    db: Session,
    *,
    org_id: UUID,
    source_id: UUID,
    external_call_id: str,
    advisor_id: UUID | None = None,
    customer_ref_hashed: str | None = None,
    started_at: datetime | None = None,
    duration_seconds: int | None = None,
    raw_audio_path: str | None = None,
) -> tuple[Call, bool]:
    call = Call(
        org_id=org_id,
        source_id=source_id,
        advisor_id=advisor_id,
        external_call_id=external_call_id,
        customer_ref_hashed=customer_ref_hashed,
        status=CallStatus.ingested,
        started_at=started_at,
        duration_seconds=duration_seconds,
        raw_audio_path=raw_audio_path,
    )
    db.add(call)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Call)
            .filter(Call.source_id == source_id, Call.external_call_id == external_call_id)
            .one()
        )
        return existing, False

    db.refresh(call)
    return call, True
