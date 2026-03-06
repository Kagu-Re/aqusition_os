from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from .models import Client


def _safe(s: str) -> str:
    return (s or "").strip()


def _slug(s: str) -> str:
    return _safe(s).lower().replace(" ", "-").replace("/", "-")


def generate_onboarding_pack(client: Client, out_root: str = "clients") -> Dict[str, str]:
    """Generate a minimal onboarding pack for a client.

    Output structure:
      clients/<client_id>/onboarding/
        - utm_policy.md
        - event_map.md
        - naming_convention.md
        - first_7_days.md

    Returns: mapping {filename: absolute_path}
    """
    client_id = _slug(getattr(client, "client_id", "") or "")
    if not client_id:
        raise ValueError("client.client_id is required")

    base = Path(out_root) / client_id / "onboarding"
    base.mkdir(parents=True, exist_ok=True)

    trade = _safe(getattr(client, "trade", "trade"))
    city = _safe(getattr(client, "geo_city", "city"))
    country = _safe(getattr(client, "geo_country", "country"))
    offer_hint = _safe(getattr(client, "notes_internal", "")) or f"{trade} services"
    phone = _safe(getattr(client, "primary_phone", ""))
    email = _safe(getattr(client, "lead_email", ""))

    # UTM policy
    utm = f"""# UTM Policy — {client_id}

This policy keeps attribution consistent across Meta + Google.

## Canonical params (v1)
- `utm_source`: platform source (`meta`, `google`)
- `utm_medium`: traffic type (`cpc`, `paid_social`)
- `utm_campaign`: stable campaign key (snake/kebab; no spaces)
- `utm_content`: creative/adset identifier
- `utm_term`: keyword (Google) or audience/angle (Meta)

## Rules
1) **Never change** `utm_campaign` mid-flight. Create a new campaign key instead.
2) `utm_content` should map to **one creative variant**.
3) Use the same `utm_campaign` across platforms only if it is truly the same experiment.

## Example (Meta)
`utm_source=meta&utm_medium=paid_social&utm_campaign={client_id}-{trade}-{city}-leadgen&utm_content=vid1-angleA&utm_term=aud-broad`

## Example (Google Search)
`utm_source=google&utm_medium=cpc&utm_campaign={client_id}-{trade}-{city}-search&utm_content=rsag1&utm_term={{keyword}}`
"""

    # Event map
    events = f"""# Event Map — {client_id}

Goal: measure funnel health without collecting personal data.

## Funnel stages (v1)
1) **Landing**: `page_view`
2) **Intent**: `view_content` (scrolled, engaged, or viewed pricing/offer block)
3) **Lead**: `generate_lead` (form submit, WhatsApp click, call click)
4) **Booking**: `booking` (appointment confirmed / deposit / calendar)

## Event definitions
- `page_view`
  - fires on page load
- `view_content`
  - fires when user reaches offer section (e.g. 50% scroll) OR clicks “Pricing”
- `generate_lead`
  - fires on: form submit OR click-to-call OR click WhatsApp/LINE
- `booking`
  - fires when booking confirmed (server-side preferred)

## Notes
- We optimize the **funnel as a system**: CTR → CVR (lead) → booking rate.
- If tracking breaks, decisions become noise. Always QA events after edits.
"""

    # Naming conventions
    naming = f"""# Naming Convention — {client_id}

Consistency prevents budget leaks.

## Client
- `client_id`: `{client_id}`
- `trade`: `{trade}`
- `geo`: `{city}, {country}`

## Campaign key format
`<client_id>-<trade>-<geo>-<objective>-v<iteration>`

Example:
- `{client_id}-{trade}-{city}-lead-v1`
- `{client_id}-{trade}-{city}-search-v1`

## Asset IDs
- creative: `cr_<format>_<angle>_<n>`
- landing sections: `sec_<purpose>_<n>`

## Guardrails
- Don’t reuse IDs for different meanings.
- If you change offer angle, bump iteration.
"""

    # First 7 days operator script
    days = f"""# First 7 Days — Operator Script ({client_id})

Offer hint: **{offer_hint}**

Contact:
- phone: `{phone or "TBD"}`
- email: `{email or "TBD"}`

## Day 0 (setup)
- Confirm offer + geo + service area
- Implement UTM policy + naming convention
- Install/verify events: page_view, view_content, generate_lead, booking
- Launch learning campaigns with tight spend caps

## Daily (Days 1–7)
1) Check spend pacing (did we blow the daily cap?)
2) Review:
   - CTR (traffic quality / creative)
   - CVR-lead (landing clarity / friction)
   - Cost/Lead (budget efficiency)
3) Record 1–3 observations + 1 decision.

## Decision rules (v1)
- Low CTR → change creative angle / audience filter / headline
- Good CTR + low CVR → fix landing offer & friction
- Good CVR + high CPL → narrow geo / refine targeting / improve quality filter
- Good CPL + low bookings → fix follow-up script + booking friction

## Outputs
- 1 screenshot or stat snapshot per day
- 1 change max per day (avoid confounding)
"""

    files = {
        "utm_policy.md": utm,
        "event_map.md": events,
        "naming_convention.md": naming,
        "first_7_days.md": days,
    }
    out = {}
    for name, content in files.items():
        path = base / name
        path.write_text(content.strip() + "\n", encoding="utf-8")
        out[name] = str(path.resolve())
    return out
