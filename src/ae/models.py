from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from .enums import (
    Trade, BusinessModel, ClientStatus, PageStatus, TemplateStatus,
    WorkType, WorkStatus, Priority, AssetType, AssetSource,
    PublishAction, LogResult, EventName,
    PaymentStatus, PaymentProvider, PaymentMethod, ReconciliationStatus, ChatProvider, MenuStatus,
)
import re
from datetime import datetime

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

class Client(BaseModel):
    client_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    trade: Trade
    business_model: BusinessModel = Field(default=BusinessModel.quote_based)
    geo_country: str = Field(default="AU")
    geo_city: str = Field(min_length=1)
    service_area: List[str] = Field(min_length=1)
    primary_phone: str = Field(min_length=3)
    lead_email: EmailStr
    status: ClientStatus = ClientStatus.draft

    hours: Optional[str] = None
    license_badges: List[str] = Field(default_factory=list)
    price_anchor: Optional[str] = None
    brand_theme: Optional[str] = None
    notes_internal: Optional[str] = None
    service_config_json: Dict[str, Any] = Field(default_factory=dict)


class TradeTemplate(BaseModel):
    """Template for auto-populating client defaults based on trade type."""
    trade: Trade
    version: str = Field(default="1.0")
    
    # Tier 2: Operational defaults
    default_hours: str
    default_license_badges: List[str] = Field(default_factory=list)
    default_price_anchor_pattern: str  # Template: "Starting from {currency}{amount}"
    default_brand_theme: str
    
    # Tier 3: Content defaults
    default_amenities: List[str] = Field(default_factory=list)
    default_testimonials_patterns: List[str] = Field(default_factory=list)  # Templates with {service_area}, {price_anchor}
    default_faq_patterns: List[str] = Field(default_factory=list)  # Templates with {hours}, {service_area}
    default_faq_qa: List[Dict[str, str]] = Field(default_factory=list)  # [{"q": "...", "a": "..."}]
    default_cta_primary: str
    default_cta_secondary: str
    
    # Service packages (for fixed_price)
    default_packages: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Media
    default_hero_image_url: Optional[str] = None
    default_gallery_images: List[str] = Field(default_factory=list)


class Template(BaseModel):
    template_id: str = Field(min_length=1)
    template_name: str = Field(min_length=1)
    template_version: str = Field(min_length=1)  # semver-ish, validated lightly
    cms_schema_version: str = Field(min_length=1)
    compatible_events_version: str = Field(min_length=1)
    status: TemplateStatus = TemplateStatus.active
    changelog: Optional[str] = None
    preview_url: Optional[str] = None

class Page(BaseModel):
    page_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    template_id: str = Field(min_length=1)
    template_version: str = Field(min_length=1)

    page_slug: str = Field(min_length=1)
    page_url: str = Field(min_length=1)
    page_status: PageStatus = PageStatus.draft
    content_version: int = 1

    service_focus: Optional[str] = None
    locale: str = "en-AU"

    @field_validator("page_slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not _SLUG_RE.match(v):
            raise ValueError("page_slug must be lowercase hyphen slug (a-z0-9 and '-')")
        return v

class Asset(BaseModel):
    asset_id: str
    client_id: str
    asset_type: AssetType
    source: AssetSource
    url: str
    license_info: Optional[str] = None
    alt_text: Optional[str] = None
    checksum: Optional[str] = None

class WorkItem(BaseModel):
    work_item_id: str
    type: WorkType
    client_id: str
    page_id: Optional[str] = None
    status: WorkStatus = WorkStatus.new
    priority: Priority = Priority.normal
    owner: str = "operator"
    acceptance_criteria: Optional[str] = None
    blocker_reason: Optional[str] = None
    links_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())

class PublishLog(BaseModel):
    log_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    client_id: str
    page_id: str
    template_id: str
    template_version: str
    content_version: int
    action: PublishAction
    result: LogResult
    notes: Optional[str] = None

class ChangeLog(BaseModel):
    log_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    client_id: str
    page_id: str
    content_version_before: int
    content_version_after: int
    changed_fields: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

class EventRecord(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    page_id: str
    event_name: EventName
    params_json: Dict[str, Any] = Field(default_factory=dict)


class OpEvent(BaseModel):
    """Operational event envelope for the internal event bus.

    This is intentionally generic and versioned to support future governance
    and projection engines.
    """

    event_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    topic: str = Field(min_length=1)
    schema_version: int = Field(default=1, ge=1)
    aggregate_type: str = Field(min_length=1)
    aggregate_id: str = Field(min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)

    actor: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None


class EventSpec(BaseModel):
    topic: str = Field(min_length=1)
    schema_version: int = Field(default=1, ge=1)
    required_keys: List[str] = Field(default_factory=list)


class TimelineItem(BaseModel):
    """Projected timeline entry derived from operational events."""

    occurred_at: datetime
    event_id: str
    topic: str
    label: str
    aggregate_type: str
    aggregate_id: str

    payload: Dict[str, Any] = Field(default_factory=dict)
    actor: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None


class PolicyAuditLog(BaseModel):
    """Append-only audit log for policy decisions.

    v1 scope: record denials (and explicit overrides) for policy engines
    like transition enforcement, schema/version gates, and guardrails.
    """

    audit_id: str
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
    policy: str = Field(min_length=1)
    decision: str = Field(min_length=1)  # allow|deny|override

    subject_type: Optional[str] = None
    subject_id: Optional[str] = None

    topic: Optional[str] = None
    schema_version: Optional[int] = None

    reason: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class WeeklySanity(BaseModel):
    week_start: str
    page_id: str
    sessions: int
    call_click: int
    quote_submit: int
    thank_you_view: int
    top_source_medium: Optional[str] = None
    anomalies: Optional[str] = None





class Menu(BaseModel):
    menu_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    language: str = Field(default="en")
    currency: str = Field(default="THB")
    status: MenuStatus = MenuStatus.draft
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str

class MenuSection(BaseModel):
    section_id: str = Field(min_length=1)
    menu_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    sort_order: int = 0

class MenuItem(BaseModel):
    item_id: str = Field(min_length=1)
    menu_id: str = Field(min_length=1)
    section_id: Optional[str] = None
    title: str = Field(min_length=1)
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_available: bool = True
    sort_order: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)


class ServicePackage(BaseModel):
    package_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    duration_min: int = Field(ge=1)
    addons: List[str] = Field(default_factory=list)
    active: bool = True
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class BookingRequest(BaseModel):
    request_id: str = Field(min_length=1)
    lead_id: int
    package_id: str = Field(min_length=1)
    preferred_window: Optional[str] = None  # "morning" | "afternoon" | "evening"
    location: Optional[str] = None
    status: str = "requested"  # requested → deposit_requested → confirmed → completed → closed
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class PaymentIntent(BaseModel):
    intent_id: str = Field(min_length=1)
    lead_id: int
    booking_request_id: str = Field(min_length=1)
    amount: float = Field(ge=0)
    method: str  # "promptpay" | "stripe" | "bank"
    status: str = "requested"  # requested → paid
    payment_link: Optional[str] = None
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class QrAttribution(BaseModel):
    attribution_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)          # e.g. "menu"
    menu_id: Optional[str] = None
    url: str = Field(min_length=1)           # URL embedded in QR (typically includes aid)
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class QrScan(BaseModel):
    scan_id: str = Field(min_length=1)
    attribution_id: str = Field(min_length=1)
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class LeadIntake(BaseModel):
    lead_id: Optional[int] = None
    ts: str
    source: Optional[str] = None
    page_id: Optional[str] = None
    client_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    message: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_term: Optional[str] = None
    utm_content: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_hint: Optional[str] = None
    spam_score: int = 0
    is_spam: int = 0
    status: str = "new"
    booking_status: str = "none"
    booking_value: Optional[float] = None
    booking_currency: Optional[str] = None
    booking_ts: Optional[str] = None
    meta_json: dict = Field(default_factory=dict)


class Payment(BaseModel):
    payment_id: str = Field(min_length=1)
    booking_id: str = Field(min_length=1)     # booking aggregate id (e.g. "lead-123")
    lead_id: int

    amount: float = Field(ge=0)
    currency: str = Field(min_length=1, default="THB")

    provider: PaymentProvider = PaymentProvider.manual
    method: PaymentMethod = PaymentMethod.other
    status: PaymentStatus = PaymentStatus.pending

    external_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    meta_json: Dict[str, Any] = Field(default_factory=dict)



class PaymentReconciliation(BaseModel):
    payment_id: str = Field(min_length=1)
    status: "ReconciliationStatus" = Field(default="unmatched")
    matched_amount: Optional[float] = None
    matched_currency: Optional[str] = None
    matched_ref: Optional[str] = None
    note: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    evidence_json: Dict[str, Any] = Field(default_factory=dict)


class ChatChannel(BaseModel):
    """Registered chat channel identity for a lead/client workflow.

    v1: channel registry only (no message ingestion). Conversation mapping lands in OP-CHAT-001B.
    """

    channel_id: str = Field(min_length=1)
    provider: ChatProvider = ChatProvider.other
    handle: str = Field(min_length=1)            # e.g. LINE userId, WhatsApp phone, Telegram chat_id
    display_name: Optional[str] = None
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())



class ChatConversation(BaseModel):
    """Mapped chat conversation thread.

    Supports linking a conversation to a lead/booking for operational traceability.
    """

    conversation_id: str = Field(min_length=1)
    channel_id: str = Field(min_length=1)
    external_thread_id: Optional[str] = None
    lead_id: Optional[str] = None
    booking_id: Optional[str] = None
    status: str = Field(default="open")
    meta_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class ChatMessage(BaseModel):
    """Stored chat message (inbound/outbound)."""

    message_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    direction: str = Field(min_length=1)  # inbound | outbound
    ts: datetime = Field(default_factory=lambda: datetime.utcnow())
    external_msg_id: Optional[str] = None
    text: Optional[str] = None
    payload_json: Dict[str, Any] = Field(default_factory=dict)


class ChatTemplate(BaseModel):
    template_key: str = Field(min_length=1)
    language: str = Field(default="en")
    body: str = Field(min_length=1)
    status: str = Field(default="active")  # active | disabled
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())


class ChatAutomation(BaseModel):
    automation_id: str = Field(min_length=1)
    conversation_id: str = Field(min_length=1)
    template_key: str = Field(min_length=1)
    due_at: datetime
    status: str = Field(default="pending")  # pending | sent | cancelled
    context_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    sent_at: Optional[datetime] = None


class Activity(BaseModel):
    activity_id: Optional[int] = None
    ts: str
    actor: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    details_json: dict = Field(default_factory=dict)

class BulkOp(BaseModel):
    bulk_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow())
    mode: str = Field(default="dry_run")        # dry_run | execute
    action: str = Field(min_length=1)          # validate | publish | pause
    selector_json: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="queued")      # queued | running | done | failed
    result_json: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class AdStat(BaseModel):
    stat_id: str
    timestamp: datetime
    page_id: str
    platform: str  # meta|google|other
    campaign_id: str | None = None
    adset_id: str | None = None
    ad_id: str | None = None
    impressions: int | None = None
    clicks: int | None = None
    spend: float | None = None
    revenue: float | None = None


class HookRetry(BaseModel):
    retry_id: str
    event_id: str
    hook_name: str
    topic: str
    attempt: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    status: str  # pending | succeeded | dead
    next_attempt_at: datetime
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime



# --- Exports (CRM) ---

class ExportField(BaseModel):
    out_key: str = Field(min_length=1)
    entity: str = Field(min_length=1)  # lead|payment
    path: str = Field(min_length=1)    # dotted path into entity model
    required: bool = False
    default: Any = None


class ExportPreset(BaseModel):
    name: str
    preset_version: int = 1
    schema_name: str
    format: str = "csv"  # csv|xlsx
    delimiter: str = ","
    sheet_name: str = "export"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    locale: str = "en"
    header_map: dict = {}
    enabled: bool = True


class ExportJob(BaseModel):
    job_id: str
    preset_name: str
    cron: str
    target: str = "local"  # local|gdrive_stub|webhook_stub
    output_dir: str = "generated/exports"
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None
    fail_count: int = 0
    last_error: str | None = None


class ExportSchema(BaseModel):
    name: str = Field(min_length=1)
    schema_version: int = Field(default=1, ge=1)
    fields: List[ExportField] = Field(default_factory=list)
    notes: Optional[str] = None



# --- Reliability / Integrity ---

class IntegrityIssue(BaseModel):
    code: str
    severity: str = Field(default="error")  # error|warning|info
    message: str
    entity_type: str | None = None
    entity_id: str | None = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class IntegrityReport(BaseModel):
    report_id: str
    created_at: str
    status: str  # ok|issues

# --- Money Board v2 / CRM Models ---

class Customer(BaseModel):
    customer_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    phone: Optional[str] = None
    email: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None
    line_id: Optional[str] = None
    whatsapp_id: Optional[str] = None
    language_pref: str = "en"
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class Booking(BaseModel):
    booking_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    lead_id: Optional[int] = None  # Link to original lead if applicable (legacy/audit)
    
    # Core Data
    channel: str  # telegram, line, web, walk_in
    status: str   # NEW, PACKAGE_SELECTED, TIME_WINDOW_SET, DEPOSIT_REQUESTED, CONFIRMED, COMPLETE, CLOSED, CANCELLED, EXPIRED
    status_reason: Optional[str] = None # e.g. "customer_cancelled", "no_show"
    
    # Package Snapshot
    package_id: str
    package_name_snapshot: str
    price_amount: float
    currency: str = "THB"
    duration_minutes: int
    addons: List[str] = Field(default_factory=list)
    quantity: int = 1
    
    # Scheduling
    preferred_time_window: Optional[str] = None # morning, afternoon, etc.
    preferred_date: Optional[str] = None # YYYY-MM-DD or 'today'
    final_slot_start: Optional[datetime] = None
    final_slot_end: Optional[datetime] = None
    
    # Payment / Deposit
    deposit_required: bool = False
    deposit_amount: float = 0.0
    deposit_status: str = "none" # none, requested, paid, refunded
    payment_link: Optional[str] = None
    payment_ref: Optional[str] = None
    
    # Meta
    tags: List[str] = Field(default_factory=list)
    notes_internal: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class BookingEvent(BaseModel):
    event_id: str = Field(min_length=1)
    booking_id: str = Field(min_length=1)
    timestamp: datetime
    event_type: str # STATE_CHANGED, MESSAGE_SENT, PAYMENT_RECEIVED, NOTE_ADDED
    actor_type: str # system, operator, customer
    actor_id: Optional[str] = None
    diff_payload: Dict[str, Any] = Field(default_factory=dict) # {before: {}, after: {}}
    meta_json: Dict[str, Any] = Field(default_factory=dict)

