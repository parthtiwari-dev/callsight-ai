import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class UserRole(str, enum.Enum):
    advisor = "advisor"
    team_leader = "team_leader"
    sales_director = "sales_director"
    admin = "admin"


class CallStatus(str, enum.Enum):
    ingested = "ingested"
    transcribing = "transcribing"
    diarizing = "diarizing"
    analyzing = "analyzing"
    scored = "scored"
    excluded_non_sales = "excluded_non_sales"
    failed = "failed"


class TagStatus(str, enum.Enum):
    active = "active"
    contested = "contested"
    dismissed = "dismissed"
    upheld = "upheld"


class ContestStatus(str, enum.Enum):
    pending = "pending"
    upheld = "upheld"
    dismissed = "dismissed"


class Organization(Base):
    __tablename__ = "organizations"

    org_id = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    teams: Mapped[list["Team"]] = relationship(back_populates="organization")


class Team(Base):
    __tablename__ = "teams"

    team_id = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.org_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    leader_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))

    organization: Mapped[Organization] = relationship(back_populates="teams")
    users: Mapped[list["User"]] = relationship(back_populates="team")


class User(Base):
    __tablename__ = "users"

    user_id = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.org_id"), nullable=False
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("teams.team_id")
    )
    external_ref: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    team: Mapped[Team | None] = relationship(back_populates="users")
    calls: Mapped[list["Call"]] = relationship(back_populates="advisor")


class CallSourceConfig(Base):
    __tablename__ = "call_source_configs"

    source_id = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.org_id"), nullable=False
    )
    adapter_type: Mapped[str] = mapped_column(String(80), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        UniqueConstraint("source_id", "external_call_id", name="uq_source_external_call"),
    )

    call_id = uuid_pk()
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.org_id"), nullable=False
    )
    advisor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("call_source_configs.source_id"), nullable=False
    )
    external_call_id: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_ref_hashed: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus), default=CallStatus.ingested, nullable=False
    )
    diarization_quality: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    raw_audio_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    advisor: Mapped[User | None] = relationship(back_populates="calls")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    analysis: Mapped["CallAnalysis | None"] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    issue_tags: Mapped[list["IssueTag"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    segment_id = uuid_pk()
    call_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("calls.call_id"), nullable=False
    )
    speaker_label: Mapped[str] = mapped_column(String(50), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(20))

    call: Mapped[Call] = relationship(back_populates="transcript_segments")


class CallAnalysis(Base):
    __tablename__ = "call_analyses"

    call_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("calls.call_id"), primary_key=True
    )
    call_summary: Mapped[str] = mapped_column(Text, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    needs_discovery_score: Mapped[float] = mapped_column(Float, nullable=False)
    product_knowledge_score: Mapped[float] = mapped_column(Float, nullable=False)
    objection_handling_score: Mapped[float] = mapped_column(Float, nullable=False)
    compliance_score: Mapped[float] = mapped_column(Float, nullable=False)
    next_step_booking_score: Mapped[float] = mapped_column(Float, nullable=False)
    coaching_notes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_model_response: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    call: Mapped[Call] = relationship(back_populates="analysis")


class IssueTag(Base):
    __tablename__ = "issue_tags"

    tag_id = uuid_pk()
    call_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("calls.call_id"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("transcript_segments.segment_id")
    )
    tag_type: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp_in_call: Mapped[float | None] = mapped_column(Float)
    quoted_line: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[TagStatus] = mapped_column(
        Enum(TagStatus), default=TagStatus.active, nullable=False
    )

    call: Mapped[Call] = relationship(back_populates="issue_tags")
    contest: Mapped["FlagContest | None"] = relationship(back_populates="tag")


class FlagContest(Base):
    __tablename__ = "flag_contests"

    contest_id = uuid_pk()
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("issue_tags.tag_id"), nullable=False
    )
    advisor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    contest_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ContestStatus] = mapped_column(
        Enum(ContestStatus), default=ContestStatus.pending, nullable=False
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    tag: Mapped[IssueTag] = relationship(back_populates="contest")


class ProcessingEvent(Base):
    __tablename__ = "processing_events"

    event_id = uuid_pk()
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("calls.call_id")
    )
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
