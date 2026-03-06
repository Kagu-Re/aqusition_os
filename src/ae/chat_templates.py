
from __future__ import annotations

"""Message Template Engine (v1).

- Code-first template registry with DB overrides.
- Safe {var} substitution (missing keys replaced with "?").
- No conditionals/loops in v1.
"""

from dataclasses import dataclass
from typing import Any, Dict
import re

from .repo_chat_templates import get_template


@dataclass(frozen=True)
class TemplateSpec:
    key: str
    body: str


DEFAULT_TEMPLATES: Dict[str, TemplateSpec] = {
    "booking_confirm": TemplateSpec(
        key="booking_confirm",
        body="✅ Booking confirmed for {service_date}. Reply YES to proceed.",
    ),
    "payment_request": TemplateSpec(
        key="payment_request",
        body="💳 Payment link: {payment_link} (amount {amount} {currency}).",
    ),
    "followup_24h": TemplateSpec(
        key="followup_24h",
        body="Just checking in — do you need any changes to your booking?",
    ),
    "cancellation_notice": TemplateSpec(
        key="cancellation_notice",
        body="Your booking was cancelled. If this is a mistake, reply HELP.",
    ),
    # Money Board templates
    "money_board.package_menu": TemplateSpec(
        key="money_board.package_menu",
        body="📋 Available packages:\n{package_list}\n\nReply with the package number you'd like to book.",
    ),
    "money_board.time_window_request": TemplateSpec(
        key="money_board.time_window_request",
        body="⏰ When would you prefer your {package_name}?\n\n• Morning (9am-12pm)\n• Afternoon (12pm-5pm)\n• Evening (5pm-9pm)\n\nReply with your preferred time.",
    ),
    "money_board.deposit_request": TemplateSpec(
        key="money_board.deposit_request",
        body="💳 To confirm your {package_name} booking, please pay the deposit of ฿{amount}.\n\nPayment link: {payment_link}\n\nOr send via PromptPay to: {promptpay_number}\n\nOnce paid, your booking will be confirmed!",
    ),
    "money_board.deposit_reminder": TemplateSpec(
        key="money_board.deposit_reminder",
        body="⏰ Reminder: Your {package_name} booking is waiting for deposit payment of ฿{amount}.\n\nPayment link: {payment_link}\n\nPlease complete payment to confirm your booking.",
    ),
    "money_board.service_reminder_24h": TemplateSpec(
        key="money_board.service_reminder_24h",
        body="📅 Reminder: Your {package_name} is scheduled for tomorrow at {time_window}.\n\nWe're looking forward to serving you!",
    ),
    "money_board.service_reminder_2h": TemplateSpec(
        key="money_board.service_reminder_2h",
        body="⏰ Your {package_name} is in 2 hours!\n\nTime: {time_window}\nLocation: {location}\n\nSee you soon!",
    ),
    "money_board.review_request": TemplateSpec(
        key="money_board.review_request",
        body="⭐ How was your {package_name} experience?\n\nWe'd love to hear your feedback! Reply with your review or rating.",
    ),
}


def _render(body: str, context: Dict[str, Any]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return str(context.get(key, "?"))
    return re.sub(r"\{([a-zA-Z0-9_]+)\}", repl, body)


def render_template(db_path: str, key: str, context: Dict[str, Any]) -> str:
    tpl = get_template(db_path, key)
    if tpl and tpl.status == "active":
        return _render(tpl.body, context)
    spec = DEFAULT_TEMPLATES.get(key)
    if not spec:
        raise ValueError(f"Unknown template key: {key}")
    return _render(spec.body, context)
