from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TranscriptSegmentResponse(BaseModel):
    segment_id: UUID | None = None
    speaker_label: str
    start_time: float
    end_time: float
    text: str
    language_code: str | None = None


class ScoreResponse(BaseModel):
    overall_score: float
    needs_discovery_score: float
    product_knowledge_score: float
    objection_handling_score: float
    compliance_score: float
    next_step_booking_score: float


class IssueTagResponse(BaseModel):
    tag_id: UUID
    call_id: UUID
    segment_id: UUID | None = None
    tag_type: str
    severity: str
    timestamp_in_call: float | None = None
    quoted_line: str | None = None
    reason: str
    confidence: float
    status: str


class ContestResponse(BaseModel):
    contest_id: UUID
    tag_id: UUID
    advisor_id: UUID
    contest_reason: str
    status: str
    reviewed_by: UUID | None = None
    created_at: datetime | None = None


class CallAnalysisResponse(BaseModel):
    call_id: UUID
    summary: str
    scores: ScoreResponse
    coaching_notes: list
    model_version: str
    tags: list[IssueTagResponse] = Field(default_factory=list)


class CallListItem(BaseModel):
    call_id: UUID
    external_call_id: str
    advisor_id: UUID | None = None
    advisor_name: str | None = None
    team_id: UUID | None = None
    status: str
    started_at: datetime | None = None
    duration_seconds: int | None = None
    overall_score: float | None = None
    active_flag_count: int


class CallDetailResponse(CallListItem):
    customer_ref_hashed: str | None = None
    source_id: UUID
    diarization_quality: str | None = None
    raw_audio_path: str | None = None
    transcript: list[TranscriptSegmentResponse] = Field(default_factory=list)
    analysis: CallAnalysisResponse | None = None
    tags: list[IssueTagResponse] = Field(default_factory=list)
    contests: list[ContestResponse] = Field(default_factory=list)


class ContestRequest(BaseModel):
    advisor_id: UUID
    contest_reason: str = Field(min_length=1)


class ContestResolutionRequest(BaseModel):
    reviewed_by: UUID
    resolution: str = Field(pattern="^(upheld|dismissed)$")


class ContestActionResponse(BaseModel):
    contest: ContestResponse
    tag: IssueTagResponse


class MockIngestRequest(BaseModel):
    external_call_id: str = "mock-api-call-001"
    advisor_ref: str = "advisor-001"
    customer_ref_hashed: str | None = "customer-demo-hash"
    started_at: datetime | None = None
    duration_seconds: int = 180
    mock: bool = True
    mock_analysis: bool = True


class IngestResponse(BaseModel):
    call_id: UUID
    created: bool
    final_status: str
    analysis_summary: str | None = None
    active_flag_count: int


class UploadRequest(BaseModel):
    metadata: MockIngestRequest = Field(default_factory=MockIngestRequest)


class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=1)


class OrgResponse(BaseModel):
    org_id: UUID
    name: str


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1)


class TeamResponse(BaseModel):
    team_id: UUID
    org_id: UUID
    name: str
    leader_user_id: UUID | None = None


class AdvisorCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    external_ref: str | None = None


class AdvisorResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    team_id: UUID | None = None
    external_ref: str | None = None
    name: str
    role: str


class DashboardSummaryResponse(BaseModel):
    calls_processed: int
    average_overall_score: float | None = None
    unresolved_critical_flag_count: int = 0
    top_issue_tags: list[dict] = Field(default_factory=list)
    team_leaderboard: list[dict] = Field(default_factory=list)
