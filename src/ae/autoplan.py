from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ActionStep:
    code: str
    title: str
    steps: List[str]


# Minimal playbook mapping (v1). Extend over time.
PLAYBOOK: Dict[str, ActionStep] = {
    "DIAG_CLICKS_NO_LEADS": ActionStep(
        code="DIAG_CLICKS_NO_LEADS",
        title="Clicks but no leads (landing/offer/tracking failure)",
        steps=[
            "Confirm landing page loads fast on mobile (<=3s) and form is visible above the fold.",
            "Verify lead form endpoint works (submit test lead, confirm it appears in DB).",
            "Verify UTM capture + page_id mapping (incoming URL -> stored lead_intake.page_id).",
            "Check spam filter thresholds (ensure real leads not classified as spam).",
            "If tracking is OK: tighten targeting + rewrite offer to match intent.",
        ],
    ),
    "DIAG_SPEND_NO_CLICKS": ActionStep(
        code="DIAG_SPEND_NO_CLICKS",
        title="Spend but no clicks (creative/target mismatch or reporting gap)",
        steps=[
            "Check ad creative rendering (image/video not rejected, correct aspect ratio).",
            "Review targeting: is audience too narrow or irrelevant?",
            "Check placement + bid strategy; try broad placements with tighter creative qualification.",
            "Confirm ad_stats ingestion isn't stale (latest date present).",
        ],
    ),
    "DIAG_LEADS_NO_BOOKINGS": ActionStep(
        code="DIAG_LEADS_NO_BOOKINGS",
        title="Leads but no bookings (mid-funnel friction or missing booking tracking)",
        steps=[
            "Verify booking proxy event fires (thank_you_view) after booking action.",
            "Ensure booking process is simple: 1 CTA, 1 booking path, minimal fields.",
            "Add follow-up automation (SMS/LINE) within 5 minutes of lead submission.",
            "Review lead quality: add qualifier question to filter low-intent leads.",
        ],
    ),
    "LOW_CTR": ActionStep(
        code="LOW_CTR",
        title="Low CTR (wasting impressions)",
        steps=[
            "Swap first-frame creative (strong hook, clear offer, local cue).",
            "Add price/eligibility qualifier to discourage low-value clicks.",
            "Split creatives by intent buckets (problem-aware vs solution-aware).",
        ],
    ),
    "HIGH_CPL": ActionStep(
        code="HIGH_CPL",
        title="High CPL (leads too expensive)",
        steps=[
            "Tighten targeting around high-intent signals (geo + service intent).",
            "Reduce friction in lead capture (fewer fields, faster page).",
            "Improve offer: add guarantee, reduce perceived risk, add scarcity.",
        ],
    ),
    "HIGH_CPA": ActionStep(
        code="HIGH_CPA",
        title="High CPA (bookings too expensive)",
        steps=[
            "Audit the booking step: remove unnecessary steps, increase trust signals.",
            "Improve lead→booking follow-up speed and script.",
            "Segment creatives by customer value (premium vs standard).",
        ],
    ),
    "LOW_LEAD_TO_BOOKING": ActionStep(
        code="LOW_LEAD_TO_BOOKING",
        title="Low lead→booking rate",
        steps=[
            "Add a qualifier on the form to filter out non-buyers (budget, timeline).",
            "Add trust signals (reviews, before/after, certifications).",
            "Improve booking CTA clarity and reduce options.",
        ],
    ),
}


def generate_autoplan(guardrails_report: Dict[str, Any]) -> Dict[str, Any]:
    """Turn guardrails findings into a concrete checklist plan."""
    findings = guardrails_report.get("findings", [])
    plans: List[Dict[str, Any]] = []

    for f in findings:
        code = f.get("code")
        page_id = f.get("page_id")
        pb = PLAYBOOK.get(code)
        if pb:
            plans.append({
                "code": pb.code,
                "page_id": page_id,
                "title": pb.title,
                "steps": pb.steps,
                "recommended_action": f.get("recommended_action"),
            })
        else:
            plans.append({
                "code": code,
                "page_id": page_id,
                "title": f.get("message", "Investigate"),
                "steps": [
                    "Inspect the KPI + diagnostics context for this finding.",
                    "Form a hypothesis (tracking vs offer vs targeting vs creative).",
                    "Apply smallest fix and re-evaluate in 24–48h.",
                ],
                "recommended_action": f.get("recommended_action"),
            })

    return {
        "summary": guardrails_report.get("summary", {}),
        "plans": plans,
    }


def render_autoplan_markdown(plan: dict) -> str:
    """Render an autoplan payload (from generate_autoplan) into markdown."""
    s = plan.get("summary", {})
    lines = [
        f"# AutoPlan for {s.get('client_id')}",
        "",
        f"- overall_status: **{s.get('overall_status')}**",
        f"- platform: {s.get('platform')}",
        f"- since_iso: {s.get('since_iso')}",
        "",
    ]
    plans = plan.get("plans", [])
    if not plans:
        lines.append("No findings → nothing to fix. ✅")
        return "\n".join(lines)

    for idx, p in enumerate(plans, start=1):
        lines.append(f"## {idx}. {p.get('title')}")
        lines.append(f"- code: `{p.get('code')}`")
        if p.get("page_id"):
            lines.append(f"- page_id: `{p.get('page_id')}`")
        if p.get("recommended_action"):
            lines.append(f"- recommended_action: `{p.get('recommended_action')}`")
        lines.append("")
        for step in p.get("steps", []):
            lines.append(f"- [ ] {step}")
        lines.append("")
    return "\n".join(lines)
