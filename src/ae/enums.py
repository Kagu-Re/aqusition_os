from __future__ import annotations

from enum import Enum

class Trade(str, Enum):
    plumber = "plumber"
    electrician = "electrician"
    roofing = "roofing"
    pest_control = "pest_control"
    hvac = "hvac"
    massage = "massage"
    spa = "spa"
    digital_literacy_workshop = "digital_literacy_workshop"

class BusinessModel(str, Enum):
    """Operational model for how clients operate."""
    quote_based = "quote_based"      # Traditional: request quote → book
    fixed_price = "fixed_price"      # Select package → book
    subscription = "subscription"     # Recurring plans
    hybrid = "hybrid"                 # Both quote and fixed-price

class ClientStatus(str, Enum):
    draft = "draft"
    qa = "qa"
    live = "live"
    paused = "paused"
    archived = "archived"

class PageStatus(str, Enum):
    draft = "draft"
    qa = "qa"
    live = "live"
    paused = "paused"

class TemplateStatus(str, Enum):
    active = "active"
    deprecated = "deprecated"

class WorkType(str, Enum):
    new_page = "new_page"
    content_update = "content_update"
    tracking_fix = "tracking_fix"
    qa_check = "qa_check"
    report = "report"

class WorkStatus(str, Enum):
    new = "new"
    ready = "ready"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"

class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"

class AssetType(str, Enum):
    logo = "logo"
    hero_image = "hero_image"
    gallery = "gallery"
    badge = "badge"
    review_image = "review_image"

class AssetSource(str, Enum):
    client_provided = "client_provided"
    stock = "stock"
    generated = "generated"

class PublishAction(str, Enum):
    publish = "publish"
    pause = "pause"
    rollback = "rollback"

class LogResult(str, Enum):
    success = "success"
    fail = "fail"

class LeadType(str, Enum):
    call = "call"
    form = "form"

class EventName(str, Enum):
    call_click = "call_click"
    quote_submit = "quote_submit"
    thank_you_view = "thank_you_view"
    package_selected = "package_selected"  # For fixed-price service package selection


class AdPlatform(str, Enum):
    meta = "meta"
    google = "google"
    other = "other"


class PaymentStatus(str, Enum):
    pending = "pending"       # created but not confirmed
    authorized = "authorized" # authorized but not captured
    captured = "captured"     # paid
    failed = "failed"
    cancelled = "cancelled"
    refunded = "refunded"

class PaymentProvider(str, Enum):
    manual = "manual"         # cash/bank transfer handled off-platform
    stripe = "stripe"
    paypal = "paypal"
    other = "other"

class PaymentMethod(str, Enum):
    cash = "cash"
    card = "card"
    bank_transfer = "bank_transfer"
    qr = "qr"                 # promptpay / qr payments
    other = "other"


class ChatProvider(str, Enum):
    """Supported chat channel providers (v1 registry).

    Conversation mapping + templates land in OP-CHAT-001B/C.
    """

    line = "line"
    whatsapp = "whatsapp"
    telegram = "telegram"
    messenger = "messenger"
    sms = "sms"
    other = "other"


class ReconciliationStatus(str, Enum):
    """Manual reconciliation workflow for payments.

    - unmatched: payment exists but has not been matched to evidence/bank/receipt
    - matched: matched to evidence and considered final
    - disputed: mismatch discovered; requires manual resolution
    - resolved: dispute resolved (may still be unmatched or matched; v1 keeps it simple)
    """

    unmatched = "unmatched"
    matched = "matched"
    disputed = "disputed"
    resolved = "resolved"


class ReconciliationStatus(str, Enum):
    """Manual reconciliation workflow for payments."""

    unmatched = "unmatched"   # created but not matched to evidence
    matched = "matched"       # matched to evidence/bank/receipt
    disputed = "disputed"     # mismatch / needs review
    resolved = "resolved"     # dispute resolved (may or may not be matched)


class MenuStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
