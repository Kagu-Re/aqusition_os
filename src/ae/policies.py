from __future__ import annotations

from typing import List, Tuple
from .models import Client, Page, Template
from .enums import EventName

REQUIRED_PAGE_EVENTS_V1 = {EventName.call_click.value, EventName.quote_submit.value, EventName.thank_you_view.value}

def publish_readiness(client: Client, page: Page, template: Template, has_events: bool) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    # Content gates
    if not client.primary_phone:
        errors.append("Missing client.primary_phone")
    if not client.lead_email:
        errors.append("Missing client.lead_email")
    if not client.service_area or len(client.service_area) < 1:
        errors.append("Missing client.service_area")

    # Page gates
    if not page.page_url:
        errors.append("Missing page.page_url")
    if not page.page_slug:
        errors.append("Missing page.page_slug")
    if not template.template_id:
        errors.append("Missing template.template_id")

    # Tracking gates (for v1, we just require a flag that tracking was tested)
    if not has_events:
        errors.append("Tracking not validated: expected events not confirmed firing")

    return (len(errors) == 0, errors)
