"""
SentinelFlow AI — Pydantic Request/Response Schemas
Covers all API endpoints with strict validation.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ══════════════════════════════════════════════════════════════
# AUTH SCHEMAS
# ══════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=4, description="User password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class MFAChallengeResponse(BaseModel):
    detail: str = "MFA_REQUIRED"
    mfa_required: bool = True


class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str
    message: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: str = ""
    role: str = "engineer"
    organization_id: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    mfa_enabled: bool
    organization_id: Optional[str]
    email_verified: bool
    login_count: int
    last_login: Optional[datetime]
    created_at: datetime


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    is_revoked: bool
    expires_at: datetime
    created_at: datetime


# ══════════════════════════════════════════════════════════════
# INCIDENT SCHEMAS
# ══════════════════════════════════════════════════════════════

class IncidentCreate(BaseModel):
    source: str
    metric_type: str
    severity: str = "WARNING"
    title: str
    description: str
    confidence_score: float = 0.0
    suggested_action: Optional[str] = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    correlation_id: str
    source: str
    metric_type: str
    severity: str
    title: str
    description: str
    status: str
    alert_count: int = 1
    confidence_score: float
    suggested_action: Optional[str]
    assigned_to: Optional[str]
    parent_incident_id: Optional[int] = None
    resolved_at: Optional[datetime]
    root_cause_json: Optional[str] = None
    k8s_analysis_json: Optional[str] = None
    explainability_json: Optional[str] = None
    priority_score: Optional[int] = 0
    sla_target: Optional[str] = None
    sla_breach_at: Optional[datetime] = None
    simulation_json: Optional[str] = None
    remediation_options_json: Optional[str] = None
    decision_graph_json: Optional[str] = None
    recommended_runbooks_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime



class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    alert_type: str
    service: str
    message: str
    timestamp: datetime


class AlertFingerprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fingerprint_hash: str
    first_alert: datetime
    last_alert_time: datetime
    alert_count: int
    alerts: list[AlertResponse] = []


class IncidentDetailResponse(IncidentResponse):
    logs: list["IncidentLogResponse"] = []
    timeline_events: list["TimelineEventResponse"] = []
    fingerprints: list[AlertFingerprintResponse] = []


class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="New status value")
    reason: Optional[str] = None


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
    total: int
    page: int
    per_page: int


# ══════════════════════════════════════════════════════════════
# INCIDENT LOG SCHEMAS
# ══════════════════════════════════════════════════════════════

class IncidentLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    message: str
    metadata_json: Optional[str]
    timestamp: datetime


# ══════════════════════════════════════════════════════════════
# TIMELINE SCHEMAS
# ══════════════════════════════════════════════════════════════

class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    title: str
    description: Optional[str]
    actor: str
    decision_rationale: Optional[str]
    confidence_at_step: Optional[float]
    duration_ms: Optional[float]
    mitre_technique: Optional[str] = None
    source_system: Optional[str] = None
    event_severity: Optional[str] = None
    parent_event_id: Optional[int] = None
    timestamp: datetime


class TimelineCreateRequest(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    actor: str = "system"
    decision_rationale: Optional[str] = None
    confidence_at_step: Optional[float] = None
    duration_ms: Optional[float] = None
    mitre_technique: Optional[str] = None
    source_system: Optional[str] = None
    event_severity: Optional[str] = None
    parent_event_id: Optional[int] = None


# ══════════════════════════════════════════════════════════════
# TELEMETRY SCHEMAS
# ══════════════════════════════════════════════════════════════

class TelemetryEvent(BaseModel):
    node_name: str = "node-01"
    pod_name: Optional[str] = None
    namespace: str = "default"
    cpu_usage: float = Field(0.0, ge=0, le=100)
    memory_usage: float = Field(0.0, ge=0, le=100)
    disk_usage: float = Field(0.0, ge=0, le=100)
    network_rx_bytes: float = 0.0
    network_tx_bytes: float = 0.0
    requests_per_sec: float = 0.0
    latency_ms: float = 0.0
    error_rate: float = 0.0


class TelemetryIngestResponse(BaseModel):
    status: str
    correlation_id: str
    anomalies_detected: list[str] = []
    message: str


# ══════════════════════════════════════════════════════════════
# AUDIT TRAIL SCHEMAS
# ══════════════════════════════════════════════════════════════

class AuditTrailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: Optional[int]
    command_checked: str
    status: str
    risk_score: float
    risk_assessment: Optional[str]
    remediation_action: Optional[str]
    performed_by: str
    hash: Optional[str]
    prev_hash: Optional[str]
    timestamp: datetime


class CommandExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Shell/kubectl command to evaluate")
    incident_id: Optional[int] = None


class CommandExecuteResponse(BaseModel):
    command: str
    status: str  # "ALLOWED" or "BLOCKED"
    risk_score: float
    risk_assessment: str
    execution_output: Optional[str] = None
    audit_id: int


# ══════════════════════════════════════════════════════════════
# PROMPT TEMPLATE SCHEMAS
# ══════════════════════════════════════════════════════════════

class PromptTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    capacity: str
    role: str
    intent: str
    subject: str
    premium_response: str
    evaluation: str
    category: str
    is_active: bool
    updated_at: datetime


class PromptTemplateCreate(BaseModel):
    id: str
    name: str
    capacity: str
    role: str
    intent: str
    subject: str
    premium_response: str
    evaluation: str
    category: str = "general"


# ══════════════════════════════════════════════════════════════
# OBSERVABILITY SCHEMAS
# ══════════════════════════════════════════════════════════════

class ObservabilityTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    correlation_id: str
    step_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    status: str
    error_message: Optional[str]
    timestamp: datetime


class ObservabilitySummaryResponse(BaseModel):
    total_traces: int
    avg_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    error_count: int
    traces_by_step: dict[str, int]


# ══════════════════════════════════════════════════════════════
# INFRASTRUCTURE SCHEMAS
# ══════════════════════════════════════════════════════════════

class PodInfo(BaseModel):
    name: str
    namespace: str
    status: str
    node: str
    cpu_usage: float
    memory_usage: float
    restart_count: int
    containers: list[dict[str, Any]] = []
    labels: dict[str, str] = {}


class ClusterTopologyResponse(BaseModel):
    nodes: list[dict[str, Any]]
    pods: list[PodInfo]
    services: list[dict[str, Any]]


# ══════════════════════════════════════════════════════════════
# FEATURE FLAG SCHEMAS
# ══════════════════════════════════════════════════════════════

class FeatureFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: bool
    description: Optional[str]
    updated_at: datetime


class FeatureFlagUpdate(BaseModel):
    value: bool


# ══════════════════════════════════════════════════════════════
# NOTIFICATION SCHEMAS
# ══════════════════════════════════════════════════════════════

class SlackWebhookPayload(BaseModel):
    text: str = ""
    channel: str = ""
    action: Optional[str] = None  # "approve", "reject"
    incident_id: Optional[int] = None


class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: Optional[int]
    channel: str
    recipient: Optional[str]
    message: str
    status: str
    response_action: Optional[str]
    timestamp: datetime


# ══════════════════════════════════════════════════════════════
# WEBSOCKET SCHEMAS
# ══════════════════════════════════════════════════════════════

class WSMessage(BaseModel):
    type: str  # "incident_update", "telemetry", "notification", "log"
    data: dict[str, Any]
    timestamp: str


# ══════════════════════════════════════════════════════════════
# RAG SCHEMAS
# ══════════════════════════════════════════════════════════════

class RAGSearchRequest(BaseModel):
    query: str
    limit: int = 3
    category: Optional[str] = None


class RAGSearchResult(BaseModel):
    id: int
    score: float
    title: str
    content: str
    tags: list[str]
    severity: str
    category: str


# ══════════════════════════════════════════════════════════════
# ENVELOPE & PAGINATION SCHEMAS
# ══════════════════════════════════════════════════════════════

class ErrorDetail(BaseModel):
    loc: Optional[list[str]] = None
    msg: str
    type: str


class ErrorResponse(BaseModel):
    detail: str
    errors: Optional[list[ErrorDetail]] = None
    code: Optional[str] = None


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    count: int


class PaginatedEnvelope(BaseModel):
    data: list[Any]
    meta: PaginationMeta


# ══════════════════════════════════════════════════════════════
# COMMENT SCHEMAS
# ══════════════════════════════════════════════════════════════

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Comment text content")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    author: str
    content: str
    created_at: datetime


# ══════════════════════════════════════════════════════════════
# THREAT INTEL SCHEMAS
# ══════════════════════════════════════════════════════════════

class NormalizedIOC(BaseModel):
    type: str  # ip, domain, hash, url, email
    value: str

class NormalizedAlert(BaseModel):
    source: str
    alert_type: str
    severity: str
    timestamp: Optional[datetime] = None
    iocs: list[NormalizedIOC] = []
    raw_data: Optional[dict[str, Any]] = None


# ══════════════════════════════════════════════════════════════
# RECOMMENDATION FEEDBACK SCHEMAS
# ══════════════════════════════════════════════════════════════

class FeedbackCreateRequest(BaseModel):
    original_recommendation: str = Field(..., description="The AI recommendation text")
    engineer_correction: str = Field(..., description="The corrected action text")
    reasoning: Optional[str] = Field(None, description="The rationale for correction")

class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    original_recommendation: str
    engineer_correction: str
    reasoning: Optional[str]
    created_at: datetime


class RunbookFeedbackRequest(BaseModel):
    runbook_id: str
    success: bool


class ExecuteRemediationRequest(BaseModel):
    option_id: str


# ══════════════════════════════════════════════════════════════
# KNOWLEDGE BASE SCHEMAS
# ══════════════════════════════════════════════════════════════

class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    category: str
    subcategory: Optional[str] = None
    tags: Optional[str] = None
    version: str
    author: str
    content: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    usage_count: int
    success_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentUpdateRequest(BaseModel):
    title: str
    category: str
    subcategory: Optional[str] = None
    tags: Optional[str] = None
    content: str
    version: str


class KnowledgeSearchResponse(BaseModel):
    id: int
    score: float
    title: str
    content: str
    tags: list[str] = []
    category: str


# ══════════════════════════════════════════════════════════════
# GOVERNANCE CONFIG SCHEMAS
# ══════════════════════════════════════════════════════════════

class ExecutionConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: str
    rate_limit_per_minute: int
    min_confidence_score: int
    max_blast_radius: int
    restricted_services: str
    low_risk_actions: str
    updated_at: datetime


class ExecutionConfigUpdateRequest(BaseModel):
    mode: str
    rate_limit_per_minute: int
    min_confidence_score: int
    max_blast_radius: int
    restricted_services: str
    low_risk_actions: str





