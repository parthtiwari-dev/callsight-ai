import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Call, CallSourceConfig, Organization
from app.db.session import Base


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_source_external_call_id_unique_constraint_blocks_duplicates(db):
    org = Organization(name="FitNova")
    db.add(org)
    db.commit()

    source = CallSourceConfig(org_id=org.org_id, adapter_type="folder", config={})
    db.add(source)
    db.commit()

    first = Call(
        org_id=org.org_id,
        source_id=source.source_id,
        external_call_id="vendor-call-001",
    )
    second = Call(
        org_id=org.org_id,
        source_id=source.source_id,
        external_call_id="vendor-call-001",
    )
    db.add(first)
    db.commit()

    db.add(second)
    with pytest.raises(IntegrityError):
        db.commit()
