from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .diagnostics import diagnose_client
from .reporting import kpi_report_for_client


@dataclass(frozen=True)
class GuardrailFinding:
    severity: str  # "crit" | "warn" | "info"
    code: str
    page_id: Optional[str]
    message: str
    details: Dict[str, Any]
    recommended_action: str


def _load_guardrails_config(path: str) -> Dict[str, Any]:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_guardrails(
    db_path: str,
    *,
    client_id: str,
    platform: str | None = None,
    since_iso: str | None = None,
    config_path: str = "config/guardrails.json",
) -> Dict[str, Any]:
    """Evaluate budget guardrails using KPI report + diagnostics.

    Produces:
      - findings: actionable guardrail findings
      - overall_status: PASS | WARN | FAIL
      - summary: counts + thresholds used

    Design intent:
      - Turn "numbers" into "decisions" (pause vs optimize vs observe).
      - Keep thresholds configurable and auditable.
    """
    cfg = _load_guardrails_config(config_path)
    thresholds = cfg.get("thresholds", {})
    actions = cfg.get("actions", {})
    booking_event_name = cfg.get("booking_event_name", "thank_you_view")

    # Base inputs
    kpi = kpi_report_for_client(db_path, client_id=client_id, platform=platform, since_iso=since_iso)
    diag = diagnose_client(
        db_path,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
        booking_event_name=booking_event_name,
    )

    findings: List[GuardrailFinding] = []

    # Map diagnostics crits directly to FAIL
    for i in diag.get("issues", []):
        sev = i["severity"]
        code = f"DIAG_{i['code']}"
        if sev == "crit":
            findings.append(GuardrailFinding(
                severity="crit",
                code=code,
                page_id=i.get("page_id"),
                message=i.get("message", ""),
                details=i.get("details", {}),
                recommended_action=actions.get("crit", "pause_or_fix_tracking"),
            ))
        elif sev == "warn":
            findings.append(GuardrailFinding(
                severity="warn",
                code=code,
                page_id=i.get("page_id"),
                message=i.get("message", ""),
                details=i.get("details", {}),
                recommended_action=actions.get("warn", "optimize"),
            ))

    # KPI threshold checks (only once signal is sufficient)
    min_clicks = int(thresholds.get("min_clicks_for_signal", 0) or 0)
    min_impr = int(thresholds.get("min_impressions_for_signal", 0) or 0)

    for r in kpi.get("rows", []):
        page_id = r["page_id"]
        impressions = int(r.get("impressions", 0) or 0)
        clicks = int(r.get("clicks", 0) or 0)
        spend = float(r.get("spend", 0.0) or 0.0)

        # Only evaluate CTR/CPC when we have enough traffic to avoid noise
        has_signal = (clicks >= min_clicks) or (impressions >= min_impr)

        if has_signal:
            min_ctr = float(thresholds.get("min_ctr", 0.0) or 0.0)
            ctr = float(r.get("ctr") or 0.0)
            if min_ctr > 0 and ctr < min_ctr and spend > 0:
                findings.append(GuardrailFinding(
                    severity="warn",
                    code="LOW_CTR",
                    page_id=page_id,
                    message="CTR below minimum threshold (wasting impressions).",
                    details={"ctr": ctr, "min_ctr": min_ctr, "impressions": impressions, "clicks": clicks, "spend": spend},
                    recommended_action=actions.get("warn", "optimize_targeting_creative_landing"),
                ))

            max_cpc = float(thresholds.get("max_cpc", 0.0) or 0.0)
            cpc = r.get("cpc")
            if max_cpc > 0 and cpc is not None and float(cpc) > max_cpc:
                findings.append(GuardrailFinding(
                    severity="warn",
                    code="HIGH_CPC",
                    page_id=page_id,
                    message="CPC above maximum threshold.",
                    details={"cpc": float(cpc), "max_cpc": max_cpc, "clicks": clicks, "spend": spend},
                    recommended_action=actions.get("warn", "optimize_targeting_creative_landing"),
                ))

        # CPL/CPA checks require conversion signal; evaluate whenever spend>0
        max_cpl = float(thresholds.get("max_cpl", 0.0) or 0.0)
        cpl = r.get("cpl")
        if max_cpl > 0 and cpl is not None and float(cpl) > max_cpl and spend > 0:
            findings.append(GuardrailFinding(
                severity="warn",
                code="HIGH_CPL",
                page_id=page_id,
                message="CPL above maximum threshold.",
                details={"cpl": float(cpl), "max_cpl": max_cpl, "leads": int(r.get("leads", 0) or 0), "spend": spend},
                recommended_action=actions.get("warn", "optimize_targeting_creative_landing"),
            ))

        max_cpa = float(thresholds.get("max_cpa", 0.0) or 0.0)
        cpa = r.get("cpa")
        if max_cpa > 0 and cpa is not None and float(cpa) > max_cpa and spend > 0:
            findings.append(GuardrailFinding(
                severity="warn",
                code="HIGH_CPA",
                page_id=page_id,
                message="CPA above maximum threshold.",
                details={"cpa": float(cpa), "max_cpa": max_cpa, "bookings": int(r.get("bookings", 0) or 0), "spend": spend},
                recommended_action=actions.get("warn", "optimize_targeting_creative_landing"),
            ))

        min_l2b = float(thresholds.get("min_lead_to_booking", 0.0) or 0.0)
        l2b = r.get("lead_to_booking")
        leads = int(r.get("leads", 0) or 0)
        if min_l2b > 0 and leads > 0 and l2b is not None and float(l2b) < min_l2b:
            findings.append(GuardrailFinding(
                severity="warn",
                code="LOW_LEAD_TO_BOOKING",
                page_id=page_id,
                message="Lead→booking rate below minimum threshold.",
                details={"lead_to_booking": float(l2b), "min_lead_to_booking": min_l2b, "leads": leads, "bookings": int(r.get("bookings", 0) or 0)},
                recommended_action=actions.get("warn", "optimize_targeting_creative_landing"),
            ))

    # Overall status
    status = "PASS"
    if any(f.severity == "crit" for f in findings):
        status = "FAIL"
    elif any(f.severity == "warn" for f in findings):
        status = "WARN"

    summary = {"crit": 0, "warn": 0, "info": 0}
    for f in findings:
        summary[f.severity] += 1

    return {
        "summary": {
            "client_id": client_id,
            "platform": platform,
            "since_iso": since_iso,
            "overall_status": status,
            "counts": summary,
            "thresholds": thresholds,
            "booking_event_name": booking_event_name,
            "config_version": cfg.get("version"),
        },
        "findings": [
            {
                "severity": f.severity,
                "code": f.code,
                "page_id": f.page_id,
                "message": f.message,
                "details": f.details,
                "recommended_action": f.recommended_action,
            }
            for f in findings
        ],
    }
