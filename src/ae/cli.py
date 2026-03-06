from __future__ import annotations

import json
import hashlib
import os
import re
from pathlib import Path
from typing import Optional, List

import typer

from ae.auth import create_user, set_password
from .metrics import capacity_snapshot
from .metrics import flow_snapshot, bottleneck_flags, sla_breaches
from .timeutils import now_utc_iso

from . import db as dbmod
from .models import Client, Template, Page
from .enums import Trade, BusinessModel, TemplateStatus, PageStatus, WorkType, Priority, EventName
from . import repo
from . import service

# helpers extracted from this module to keep cli.py navigable
from .cli_support import (
    _build_adapter_override,
    _compute_preflight_report,
    _read_env,
    _load_sla_policy,
    _load_json,
    _resolve_preflight_policy,
)

app = typer.Typer(add_completion=False)

@app.command("migrate-workqueue")
def migrate_workqueue(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
):
    """Migrate WORK_QUEUE.md to latest schema (adds client_id column)."""
    from .migrations import migrate_work_queue_add_client_id

    ok = migrate_work_queue_add_client_id(work_queue_path)
    if not ok:
        raise typer.BadParameter("Migration failed or WORK_QUEUE not found")

    typer.echo("WORK_QUEUE.md migrated (client_id column ensured)")

@app.command()
def init_db(db: str = typer.Option(..., help="Path to sqlite db file")):
    """Initialize sqlite schema."""
    dbmod.init_db(db)
    typer.echo(f"OK: initialized {db}")

@app.command()
def create_template(
    db: str = typer.Option(...),
    template_id: str = typer.Option(...),
    version: str = typer.Option(...),
    cms_schema: str = typer.Option(...),
    events: str = typer.Option(...),
    name: str = typer.Option("Trades LP Template"),
    status: TemplateStatus = typer.Option(TemplateStatus.active),
):
    t = Template(
        template_id=template_id,
        template_name=name,
        template_version=version,
        cms_schema_version=cms_schema,
        compatible_events_version=events,
        status=status,
    )
    repo.upsert_template(db, t)
    typer.echo(f"OK: template {template_id}@{version}")

@app.command()
def create_client(
    db: str = typer.Option(...),
    client_id: str = typer.Option(...),
    name: str = typer.Option(...),
    trade: Trade = typer.Option(...),
    city: str = typer.Option(...),
    phone: str = typer.Option(...),
    email: str = typer.Option(...),
    service_area: List[str] = typer.Option(..., help="Repeatable. Example: --service-area 'Brisbane North'"),
    country: str = typer.Option("TH", help="Country code (ISO, e.g., AU, TH, US)"),
    business_model: BusinessModel = typer.Option(BusinessModel.quote_based, help="Business model"),
    no_defaults: bool = typer.Option(False, "--no-defaults", help="Skip auto-population of defaults from trade template"),
):
    """Create a new client with optional auto-population of defaults from trade template."""
    c = Client(
        client_id=client_id,
        client_name=name,
        trade=trade,
        geo_country=country.upper(),
        geo_city=city,
        service_area=service_area,
        primary_phone=phone,
        lead_email=email,
        business_model=business_model,
    )
    
    apply_defaults = not no_defaults
    repo.upsert_client(db, c, apply_defaults=apply_defaults)
    
    # Retrieve the client to show what was applied
    stored = repo.get_client(db, client_id=client_id)
    if not stored:
        typer.echo(f"ERROR: Failed to retrieve client {client_id}")
        raise typer.Exit(1)
    
    typer.echo(f"OK: client {client_id} created")
    
    if apply_defaults:
        typer.echo("\nApplied defaults from trade template:")
        if stored.hours:
            typer.echo(f"  - Hours: {stored.hours}")
        if stored.license_badges:
            typer.echo(f"  - License badges: {', '.join(stored.license_badges)}")
        if stored.price_anchor:
            typer.echo(f"  - Price anchor: {stored.price_anchor}")
        if stored.brand_theme:
            typer.echo(f"  - Brand theme: {stored.brand_theme}")
        if stored.service_config_json:
            config = stored.service_config_json
            if config.get("default_amenities"):
                typer.echo(f"  - Default amenities: {len(config['default_amenities'])} items")
            if config.get("default_testimonials"):
                typer.echo(f"  - Default testimonials: {len(config['default_testimonials'])} items")
            if config.get("default_faq"):
                typer.echo(f"  - Default FAQ: {len(config['default_faq'])} items")
        
        # Check if packages were created
        from .repo_service_packages import list_packages
        packages = list_packages(db, client_id=client_id, active=True)
        if packages:
            typer.echo(f"  - Service packages: {len(packages)} created")
            for pkg in packages:
                typer.echo(f"    * {pkg.name} (${pkg.price})")
    else:
        typer.echo("\nDefaults skipped (--no-defaults flag used)")

@app.command()

@app.command()
def generate_onboarding(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    out_root: str = typer.Option("clients", help="Output root directory (default: clients/)"),
):
    """Generate per-client onboarding markdown pack (UTM policy, event map, naming, first 7 days)."""
    from . import repo
    from .onboarding import generate_onboarding_pack

    c = repo.get_client(db, client_id=client_id)
    if not c:
        raise typer.BadParameter(f"client not found: {client_id}")

    files = generate_onboarding_pack(c, out_root=out_root)
    typer.echo(json.dumps({"ok": True, "client_id": client_id, "files": files}, indent=2))


@app.command()
def create_page(
    db: str = typer.Option(...),
    page_id: str = typer.Option(...),
    client_id: str = typer.Option(...),
    template_id: str = typer.Option(...),
    slug: str = typer.Option(...),
    url: str = typer.Option(...),
):
    template = repo.get_template(db, template_id)
    if not template:
        raise typer.BadParameter(f"Template not found: {template_id}")
    p = Page(
        page_id=page_id,
        client_id=client_id,
        template_id=template_id,
        template_version=template.template_version,
        page_slug=slug,
        page_url=url,
        page_status=PageStatus.draft,
        content_version=1,
    )
    repo.upsert_page(db, p)
    typer.echo(f"OK: page {page_id} (draft)")


@app.command()
def ads_simulate(
    platform: str = typer.Option(..., help="Platform: meta|google"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    date_from: str = typer.Option("2026-01-01", help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option("2026-01-07", help="End date YYYY-MM-DD"),
):
    """Simulate ads platform pulls (spend + results) using deterministic stubs."""
    from .ads import get_ads_adapter

    a = get_ads_adapter(platform)
    spend = a.pull_spend(client_id=client_id, date_from=date_from, date_to=date_to)
    results = a.pull_results(client_id=client_id, date_from=date_from, date_to=date_to)
    payload = {
        "ok": True,
        "platform": a.platform,
        "client_id": client_id,
        "date_from": date_from,
        "date_to": date_to,
        "spend": spend.__dict__,
        "results": results.__dict__,
    }
    typer.echo(json.dumps(payload, indent=2))



@app.command()
def ads_pull_stats(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    platform: str = typer.Option(..., help="Platform: meta|google"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    date_from: str = typer.Option("2026-01-01", help="Start date YYYY-MM-DD"),
    date_to: str = typer.Option("2026-01-07", help="End date YYYY-MM-DD"),
):
    """Pull (stub) ads stats and write synthetic rows into `ad_stats` for all pages of a client."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from .ads import get_ads_adapter
    from .models import AdStat
    from . import repo

    pages = repo.list_pages_filtered(db, client_id=client_id, limit=500)
    if not pages:
        raise typer.BadParameter(f"no pages found for client_id={client_id}")

    a = get_ads_adapter(platform)
    spend = a.pull_spend(client_id=client_id, date_from=date_from, date_to=date_to)
    results = a.pull_results(client_id=client_id, date_from=date_from, date_to=date_to)

    # Distribute totals evenly across pages (v1). Later we can use campaign/adset granularity.
    per_page_impr = int((spend.impressions or 0) / len(pages)) if spend.impressions is not None else None
    per_page_clicks = int((spend.clicks or 0) / len(pages)) if spend.clicks is not None else None
    per_page_spend = float((spend.spend or 0.0) / len(pages)) if spend.spend is not None else None
    per_page_rev = float((results.revenue or 0.0) / len(pages)) if results.revenue is not None else None

    ts = datetime.now(timezone.utc)

    inserted = []
    for p in pages:
        stat = AdStat(
            stat_id=str(uuid4()),
            timestamp=ts,
            page_id=p.page_id,
            platform=a.platform,
            impressions=per_page_impr,
            clicks=per_page_clicks,
            spend=per_page_spend,
            revenue=per_page_rev,
        )
        repo.insert_ad_stat(db, stat)
        inserted.append({"page_id": p.page_id, "stat_id": stat.stat_id})

    # Activity log for traceability
    repo.append_activity(
        db,
        action="ads_pull_stats",
        entity_type="client",
        entity_id=client_id,
        actor="cli",
        details={"platform": a.platform, "pages": len(pages), "date_from": date_from, "date_to": date_to},
    )

    typer.echo(json.dumps({
        "ok": True,
        "platform": a.platform,
        "client_id": client_id,
        "pages": len(pages),
        "inserted": inserted,
        "totals": {"spend": spend.__dict__, "results": results.__dict__},
    }, indent=2))



@app.command('kpi-client-report')
def kpi_client_report(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    window: Optional[str] = typer.Option(None, help="Convenience time window like 7d, 30d (mutually exclusive with since_iso)"),
    fmt: str = typer.Option("json", help="Output format: json|markdown"),
):
    """Generate KPI report per page (ad_stats + lead_intake + booking events)."""
    from .reporting import kpi_report_for_client

    report = kpi_report_for_client(db, client_id=client_id, platform=platform, since_iso=since_iso)
    if fmt.strip().lower() == "json":
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if fmt.strip().lower() != "markdown":
        raise typer.BadParameter("fmt must be json or markdown")

    # Markdown table
    rows = report["rows"]
    header = "| page_id | impressions | clicks | spend | ctr | cpc | leads | bookings | cpl | cpa | roas |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [header]
    for r in rows:
        lines.append(
            f"| {r['page_id']} | {r['impressions']} | {r['clicks']} | {r['spend']:.2f} | "
            f"{(r['ctr'] or 0):.4f} | {(r['cpc'] or 0):.2f} | {r['leads']} | {r['bookings']} | {(r['cpl'] or 0):.2f} | {(r['cpa'] or 0):.2f} | {(r['roas'] or 0):.2f} |"
        )
    typer.echo("\n".join(lines))



@app.command("diagnostics-client")
def diagnostics_client(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    booking_event_name: str = typer.Option("thank_you_view", help="Event name treated as booking proxy"),
    fmt: str = typer.Option("json", help="Output format: json|markdown"),
):
    """Run diagnostics to detect tracking gaps and guardrail risks."""
    from .diagnostics import diagnose_client

    report = diagnose_client(
        db,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
        booking_event_name=booking_event_name,
    )

    if fmt.strip().lower() == "json":
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if fmt.strip().lower() != "markdown":
        raise typer.BadParameter("fmt must be json or markdown")

    s = report["summary"]
    lines = [
        f"# Diagnostics for {s['client_id']}",
        "",
        f"- platform: {s['platform']}",
        f"- since_iso: {s['since_iso']}",
        f"- issues: total={s['total_issues']} crit={s['counts']['crit']} warn={s['counts']['warn']} info={s['counts']['info']}",
        "",
        "| severity | code | page_id | message |",
        "|---|---|---|---|",
    ]
    for i in report["issues"]:
        msg = (i["message"] or "").replace("|", "\\|")
        lines.append(f"| {i['severity']} | {i['code']} | {i['page_id'] or ''} | {msg} |")
    typer.echo("\n".join(lines))



@app.command("guardrails-evaluate")
def guardrails_evaluate(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    window: Optional[str] = typer.Option(None, help="Convenience time window like 7d, 30d (mutually exclusive with since_iso)"),
    config_path: str = typer.Option("config/guardrails.json", help="Path to guardrails config JSON"),
    write_patch_queue: bool = typer.Option(False, help="Append a patch item to ops/PATCH_QUEUE.md when FAIL/CRIT"),
    fmt: str = typer.Option("json", help="Output format: json|markdown"),
):
    """Evaluate budget guardrails and (optionally) append a patch queue item when risk is high."""
    from datetime import datetime, timezone
    if window and since_iso:
        raise typer.BadParameter("Provide either --since-iso or --window, not both")
    if window and not since_iso:
        from .timewindow import window_to_since_iso
        since_iso = window_to_since_iso(window).since_iso
    from .guardrails import evaluate_guardrails

    report = evaluate_guardrails(
        db,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
        config_path=config_path,
    )

    if write_patch_queue:
        overall = report["summary"]["overall_status"]
        crits = report["summary"]["counts"]["crit"]
        if overall == "FAIL" or crits > 0:
            stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            item = f"\n- [{stamp}] Guardrails FAIL for client={client_id} platform={platform or 'all'}: review tracking + pause/adjust spend. Findings={len(report['findings'])}\n"
            try:
                with open("ops/PATCH_QUEUE.md", "a", encoding="utf-8") as f:
                    f.write(item)
            except FileNotFoundError:
                # ignore if ops not present in runtime env
                pass

    if fmt.strip().lower() == "json":
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if fmt.strip().lower() != "markdown":
        raise typer.BadParameter("fmt must be json or markdown")

    s = report["summary"]
    lines = [
        f"# Guardrails for {s['client_id']}",
        "",
        f"- overall_status: **{s['overall_status']}**",
        f"- platform: {s['platform']}",
        f"- since_iso: {s['since_iso']}",
        f"- counts: crit={s['counts']['crit']} warn={s['counts']['warn']} info={s['counts']['info']}",
        "",
        "| severity | code | page_id | message | action |",
        "|---|---|---|---|---|",
    ]
    for fnd in report["findings"]:
        msg = (fnd["message"] or "").replace("|", "\\|")
        act = (fnd["recommended_action"] or "").replace("|", "\\|")
        lines.append(f"| {fnd['severity']} | {fnd['code']} | {fnd['page_id'] or ''} | {msg} | {act} |")
    typer.echo("\n".join(lines))




@app.command("guardrails-autoplan")
def guardrails_autoplan(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    window: Optional[str] = typer.Option(None, help="Convenience time window like 7d, 30d (mutually exclusive with since_iso)"),
    config_path: str = typer.Option("config/guardrails.json", help="Path to guardrails config JSON"),
    fmt: str = typer.Option("markdown", help="Output format: json|markdown"),
    write_patch_queue: bool = typer.Option(False, help="Append autoplan to ops/PATCH_QUEUE.md with deterministic ID"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="Patch queue file path"),
):
    """Generate a concrete action checklist from guardrails findings."""
    from .guardrails import evaluate_guardrails
    from .autoplan import generate_autoplan, render_autoplan_markdown

    if window and since_iso:
        raise typer.BadParameter("Provide either --since-iso or --window, not both")
    if window and not since_iso:
        from .timewindow import window_to_since_iso
        since_iso = window_to_since_iso(window).since_iso

    report = evaluate_guardrails(
        db,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
        config_path=config_path,
    )
    plan = generate_autoplan(report)

    if fmt.strip().lower() == "json":
        typer.echo(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    if fmt.strip().lower() != "markdown":
        raise typer.BadParameter("fmt must be json or markdown")

    md = render_autoplan_markdown(plan)

    if write_patch_queue:
        from .ops_writer import make_patch_item, append_patch_queue
        s = plan.get("summary", {})
        item = make_patch_item(
            client_id=s.get("client_id") or client_id,
            platform=s.get("platform") or platform,
            overall_status=s.get("overall_status") or "UNKNOWN",
            since_iso=s.get("since_iso") or since_iso,
            content_md=md,
        )
        append_patch_queue(patch_queue_path, item)

    typer.echo(md)




@app.command("ops-run")
def ops_run(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    window: Optional[str] = typer.Option(None, help="Convenience time window like 7d, 30d (mutually exclusive with since_iso)"),
    config_path: str = typer.Option("config/guardrails.json", help="Path to guardrails config JSON"),
    assignee: str = typer.Option("unassigned", help="Who owns execution"),
    status: str = typer.Option("open", help="open|doing|blocked|done"),
    auto_start: bool = typer.Option(False, help="If set, immediately start newly created work items"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="Patch queue file path"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="Work queue file path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="Log horizon file path"),
):
    """Run the ops cadence: AutoPlan→PATCH_QUEUE, promote new patches→WORK_QUEUE, optionally start."""
    from .timewindow import window_to_since_iso
    from .autoplan import generate_autoplan, render_autoplan_markdown
    from .guardrails import evaluate_guardrails
    from .ops_writer import make_patch_item, append_patch_queue
    from .patchqueue import list_patch_ids, find_patch_entry
    from .workqueue import make_work_item, append_work_queue, start_work, append_log_horizon

    if window and since_iso:
        raise typer.BadParameter("Provide either --since-iso or --window, not both")
    if window and not since_iso:
        since_iso = window_to_since_iso(window).since_iso

    before_ids = list_patch_ids(patch_queue_path)

    report = evaluate_guardrails(
        db,
        client_id=client_id,
        platform=platform,
        since_iso=since_iso,
        config_path=config_path,
    )
    plan = generate_autoplan(report)
    md = render_autoplan_markdown(plan)

    s = plan.get("summary", {})
    item = make_patch_item(
        client_id=s.get("client_id") or client_id,
        platform=s.get("platform") or platform,
        overall_status=s.get("overall_status") or "UNKNOWN",
        since_iso=s.get("since_iso") or since_iso,
        content_md=md,
    )
    append_patch_queue(patch_queue_path, item)

    after_ids = list_patch_ids(patch_queue_path)
    new_ids = [pid for pid in after_ids if pid.lower() not in {x.lower() for x in before_ids}]

    promoted = []
    started = []

    for pid in new_ids:
        entry = find_patch_entry(patch_queue_path, pid)
        title = entry.title_line[3:].strip() if entry and entry.title_line.startswith("## ") else f"AutoPlan {pid}"
        title = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}T[^\)]+\)\s*$", "", title).strip()

        wi = make_work_item(patch_id=pid, client_id=client_id, title=title, assignee=assignee, status=status)
        append_work_queue(work_queue_path, wi)
        promoted.append(wi.work_id)

        if auto_start:
            start_work(work_queue_path, wi.work_id)
            started.append(wi.work_id)

    # log
    msg = [
        f"- ops_run: client_id=`{client_id}` platform=`{platform or 'all'}`",
        f"- autoplan_patch_id: `{item.patch_id}`",
        f"- promoted: {', '.join(promoted) if promoted else '(none)'}",
    ]
    if started:
        msg.append(f"- started: {', '.join(started)}")
    append_log_horizon(log_path, "\n".join(msg))

    typer.echo(json.dumps({
        "autoplan_patch_id": item.patch_id,
        "promoted_work_ids": promoted,
        "started_work_ids": started,
    }, indent=2))


@app.command("patchqueue-to-work")
def patchqueue_to_work(
    patch_id: str = typer.Option(..., help="Patch ID like AP-xxxxxxxxxx"),
    assignee: str = typer.Option("unassigned", help="Who owns execution"),
    status: str = typer.Option("open", help="open|doing|blocked|done"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="Input PATCH_QUEUE.md path"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="Output WORK_QUEUE.md path"),
):
    """Promote a PATCH_QUEUE item into WORK_QUEUE (dedup by work_id)."""
    from .patchqueue import find_patch_entry
    from .workqueue import make_work_item, append_work_queue

    entry = find_patch_entry(patch_queue_path, patch_id)
    if entry is None:
        raise typer.BadParameter(f"patch_id not found in {patch_queue_path}: {patch_id}")
    # Extract client_id from patch section (preferred: `client_id: ...`).
    m_cid = re.search(r"\bclient_id\s*[:=]\s*`?([a-zA-Z0-9_-]+)`?", entry.section_md)
    client_id = m_cid.group(1) if m_cid else ""
    if client_id.strip() == "":
        typer.echo("client_id is required in patch section (add `client_id: <id>`)", err=True)
        raise typer.Exit(code=1)


    # Title: reuse heading line without timestamp noise if possible
    title = entry.title_line
    # strip leading '## '
    if title.startswith("## "):
        title = title[3:]
    # optional: strip trailing timestamp in parentheses
    title = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}T[^\)]+\)\s*$", "", title).strip()

    item = make_work_item(patch_id=patch_id, client_id=client_id, title=title, assignee=assignee, status=status)
    append_work_queue(work_queue_path, item)
    typer.echo(f"Promoted {patch_id} -> {work_queue_path} as {item.work_id}")


@app.command("guardrails-dashboard")
def guardrails_dashboard(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    platform: Optional[str] = typer.Option(None, help="Platform filter: meta|google"),
    since_iso: Optional[str] = typer.Option(None, help="Only include data since ISO timestamp (UTC)"),
    window: Optional[str] = typer.Option(None, help="Convenience time window like 7d, 30d (mutually exclusive with since_iso)"),
    config_path: str = typer.Option("config/guardrails.json", help="Path to guardrails config JSON"),
    client_status: Optional[str] = typer.Option("live", help="Filter clients by status (e.g. live, draft)"),
    limit_clients: int = typer.Option(200, help="Max clients to evaluate"),
    fmt: str = typer.Option("markdown", help="Output format: json|markdown"),
):
    """Fleet view: PASS/WARN/FAIL stoplights across clients."""
    from .dashboard import stoplight_dashboard
    if window and since_iso:
        raise typer.BadParameter("Provide either --since-iso or --window, not both")
    if window and not since_iso:
        from .timewindow import window_to_since_iso
        since_iso = window_to_since_iso(window).since_iso

    report = stoplight_dashboard(
        db,
        platform=platform,
        since_iso=since_iso,
        config_path=config_path,
        client_status=client_status,
        limit_clients=limit_clients,
    )

    if fmt.strip().lower() == "json":
        typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if fmt.strip().lower() != "markdown":
        raise typer.BadParameter("fmt must be json or markdown")

    s = report["summary"]
    lines = [
        "# Guardrails dashboard",
        "",
        f"- platform: {s['platform']}",
        f"- since_iso: {s['since_iso']}",
        f"- client_status_filter: {s['client_status_filter']}",
        f"- clients_evaluated: {s['clients_evaluated']}",
        f"- counts: FAIL={s['counts'].get('FAIL',0)} WARN={s['counts'].get('WARN',0)} PASS={s['counts'].get('PASS',0)}",
        "",
        "| status | client_id | crit | warn | info | findings |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in report["rows"]:
        lines.append(f"| {r['status']} | {r['client_id']} | {r['crit']} | {r['warn']} | {r['info']} | {r['total_findings']} |")
    typer.echo("\n".join(lines))




@app.command("work-list")
def work_list(
    status: Optional[str] = typer.Option(None, help="Filter by status: open|doing|blocked|done"),
    assignee: Optional[str] = typer.Option(None, help="Filter by assignee"),
    limit: int = typer.Option(50, help="Max rows to print"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON instead of table"),
):
    """List work items from WORK_QUEUE.md."""
    from .workqueue_reader import read_work_queue, filter_work

    rows = filter_work(read_work_queue(work_queue_path), status=status, assignee=assignee)
    rows = rows[: max(0, limit)]

    if as_json:
        typer.echo(json.dumps([r.__dict__ for r in rows], indent=2))
        return

    # pretty-ish fixed table
    cols = ["work_id", "status", "assignee", "created_utc", "title"]
    typer.echo(" | ".join(cols))
    typer.echo("-|-".join(["-" * len(c) for c in cols]))
    for r in rows:
        typer.echo(f"{r.work_id} | {r.status} | {r.assignee} | {r.created_utc} | {r.title}")


@app.command("work-show")
def work_show(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Show a single work item."""
    from .workqueue_reader import find_work

    r = find_work(work_queue_path, work_id)
    if r is None:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    if as_json:
        typer.echo(json.dumps(r.__dict__, indent=2))
        return

    typer.echo(f"work_id: {r.work_id}")
    typer.echo(f"patch_id: {r.patch_id}")
    typer.echo(f"status: {r.status}")
    typer.echo(f"assignee: {r.assignee}")
    typer.echo(f"created_utc: {r.created_utc}")
    typer.echo(f"started_utc: {r.started_utc}")
    typer.echo(f"done_utc: {r.done_utc}")
    typer.echo(f"title: {r.title}")
    typer.echo(f"notes: {r.notes}")


@app.command("ops-status")
def ops_status(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """High-level operational snapshot (counts + top blocked reasons)."""
    from collections import Counter
    from .workqueue_reader import read_work_queue

    rows = read_work_queue(work_queue_path)
    status_counts = Counter([r.status.lower() for r in rows])

    # blocker reasons: take notes that contain 'BLOCKED:' and count them
    reasons = []
    for r in rows:
        if r.status.lower() == "blocked" and "BLOCKED:" in (r.notes or ""):
            # take substring after first BLOCKED:
            idx = r.notes.find("BLOCKED:")
            reasons.append(r.notes[idx + len("BLOCKED:"):].strip())
    top_reasons = Counter(reasons).most_common(5)

    payload = {
        "work_total": len(rows),
        "status_counts": dict(status_counts),
        "top_blocked_reasons": [{"reason": k, "count": v} for k, v in top_reasons],
        "paths": {
            "work_queue": work_queue_path,
            "patch_queue": patch_queue_path,
            "log_horizon": log_path,
        }
    }

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"work_total: {payload['work_total']}")
    typer.echo(f"status_counts: {payload['status_counts']}")
    if payload["top_blocked_reasons"]:
        typer.echo("top_blocked_reasons:")
        for r in payload["top_blocked_reasons"]:
            typer.echo(f"- {r['count']} × {r['reason']}")


@app.command("work-start")
def work_start(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    policy_path: str = typer.Option("ops/PREFLIGHT_POLICY.json", help="Preflight policy JSON (defaults)"),
    env_path: str = typer.Option("ops/ENV.json", help="ENV.json path (dev/staging/prod)"),
    profiles_path: str = typer.Option("ops/PREFLIGHT_PROFILES.json", help="Profile policies by environment"),
    require_clean: bool = typer.Option(False, help="Run preflight gate before starting work"),
    max_actionable: int = typer.Option(0, help="If require_clean, fail if actionable issues > this (overrides config when set)"),
    stale_days: int = typer.Option(7, help="If require_clean, stale threshold in days (overrides config when set)"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Mark a work item as doing and stamp started_utc."""
    if require_clean:
        pol = _resolve_preflight_policy(
            work_queue_path=work_queue_path,
            patch_queue_path=patch_queue_path,
            stale_days=stale_days,
            max_actionable=max_actionable,
            policy_path=policy_path,
            env_path=env_path,
            profiles_path=profiles_path,
        )
        eff = pol["effective"]
        rep = _compute_preflight_report(work_queue_path, patch_queue_path, stale_days=eff["stale_days"])
        actionable0 = len(rep["actionable"])
        if actionable0 > eff["max_actionable"]:
            raise typer.BadParameter(
                f"preflight gate failed (env={pol['environment']}): "
                f"actionable={actionable0} > max_actionable={eff['max_actionable']}. "
                f"Run `ae preflight` or `ae work-fix`."
            )

    from .workqueue import start_work, append_log_horizon
    ok = start_work(work_queue_path, work_id)
    if not ok:
        raise typer.Exit(code=1)

    append_log_horizon(log_path, f"work_start | {work_id}")



@app.command("work-validate")
def work_validate(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    stale_days: int = typer.Option(7, help="Stale threshold in days"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Validate WORK_QUEUE integrity and flag operational risks."""
    from collections import Counter
    from .workqueue_reader import read_work_queue
    from .metrics import stale_work

    rows = read_work_queue(work_queue_path)

    missing_client = [r for r in rows if (r.client_id or "").strip() == ""]
    bad_status = [r for r in rows if r.status.lower() not in ("open", "doing", "blocked", "done")]
    blocked = [r for r in rows if r.status.lower() == "blocked"]
    stale = stale_work(rows, days=stale_days)

    # basic blocked reason completeness
    blocked_no_reason = []
    for r in blocked:
        notes = r.notes or ""
        if "BLOCKED:" not in notes:
            blocked_no_reason.append(r)

    rep = {
        "total": len(rows),
        "missing_client_id": len(missing_client),
        "bad_status": len(bad_status),
        "blocked": len(blocked),
        "blocked_no_reason": len(blocked_no_reason),
        "stale_days": stale_days,
        "stale": [s.__dict__ for s in stale[:50]],
        "examples": {
            "missing_client_id": [{"work_id": r.work_id, "patch_id": r.patch_id, "title": r.title} for r in missing_client[:10]],
            "bad_status": [{"work_id": r.work_id, "status": r.status} for r in bad_status[:10]],
            "blocked_no_reason": [{"work_id": r.work_id, "title": r.title} for r in blocked_no_reason[:10]],
        },
    }

    if as_json:
        typer.echo(json.dumps(rep, indent=2))
        return

    typer.echo(f"total: {rep['total']}")
    typer.echo(f"missing_client_id: {rep['missing_client_id']}")
    typer.echo(f"bad_status: {rep['bad_status']}")
    typer.echo(f"blocked: {rep['blocked']}")
    typer.echo(f"blocked_no_reason: {rep['blocked_no_reason']}")
    typer.echo(f"stale(>{stale_days}d): {len(rep['stale'])}")
    if rep["examples"]["missing_client_id"]:
        typer.echo("missing_client_id examples:")
        for e in rep["examples"]["missing_client_id"]:
            typer.echo(f"- {e['work_id']} | {e['patch_id']} | {e['title']}")
    if rep["examples"]["blocked_no_reason"]:
        typer.echo("blocked_no_reason examples:")
        for e in rep["examples"]["blocked_no_reason"]:
            typer.echo(f"- {e['work_id']} | {e['title']}")



@app.command("work-fix")
def work_fix(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    stale_days: int = typer.Option(7, help="Stale threshold in days"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """One-shot repair + validation pass for WORK_QUEUE integrity.

    Steps:
    1) Backfill missing client_id from PATCH_QUEUE.
    2) Validate queue (missing client_id, bad statuses, blocked-no-reason, stale work).

    Outputs a minimal actionable list when issues remain.
    """
    from .workqueue import backfill_client_ids
    from .workqueue_reader import read_work_queue
    from .metrics import stale_work

    backfill = backfill_client_ids(work_queue_path, patch_queue_path)
    rows = read_work_queue(work_queue_path)

    missing_client = [r for r in rows if (r.client_id or "").strip() == ""]
    bad_status = [r for r in rows if r.status.lower() not in ("open", "doing", "blocked", "done")]
    blocked = [r for r in rows if r.status.lower() == "blocked"]
    blocked_no_reason = [r for r in blocked if "BLOCKED:" not in (r.notes or "")]
    stale = stale_work(rows, days=stale_days)

    actionable = []
    # prioritize: missing_client_id, bad_status, blocked_no_reason, stale
    for r in missing_client[:25]:
        actionable.append({"work_id": r.work_id, "patch_id": r.patch_id, "issue": "missing_client_id", "action": "Add client_id in PATCH_QUEUE + rerun backfill"})
    for r in bad_status[:25]:
        actionable.append({"work_id": r.work_id, "patch_id": r.patch_id, "issue": "bad_status", "action": "Fix status to one of: open/doing/blocked/done"})
    for r in blocked_no_reason[:25]:
        actionable.append({"work_id": r.work_id, "patch_id": r.patch_id, "issue": "blocked_no_reason", "action": "Add notes with BLOCKED: <reason>"})
    for s in stale[:25]:
        actionable.append({"work_id": s.work_id, "patch_id": s.patch_id, "issue": "stale", "action": "Resume or close; add next-step notes"})

    rep = {
        "backfill": backfill,
        "validate": {
            "total": len(rows),
            "missing_client_id": len(missing_client),
            "bad_status": len(bad_status),
            "blocked": len(blocked),
            "blocked_no_reason": len(blocked_no_reason),
            "stale_days": stale_days,
            "stale_count": len(stale),
        },
        "actionable": actionable,
    }

    if as_json:
        typer.echo(json.dumps(rep, indent=2))
        return

    typer.echo("work-fix:")
    typer.echo(f"- backfill: scanned={backfill['scanned']} updated={backfill['updated']} missing_after={backfill['missing_after']}")
    v = rep["validate"]
    typer.echo(f"- validate: total={v['total']} missing_client_id={v['missing_client_id']} bad_status={v['bad_status']} blocked_no_reason={v['blocked_no_reason']} stale(>{stale_days}d)={v['stale_count']}")
    if rep["actionable"]:
        typer.echo("actionable (top):")
        for a in rep["actionable"][:15]:
            typer.echo(f"- {a['issue']} | {a['work_id']} | {a['patch_id']} | {a['action']}")




@app.command("env")
def env(
    env_path: str = typer.Option("ops/ENV.json", help="ENV.json path"),
    profiles_path: str = typer.Option("ops/PREFLIGHT_PROFILES.json", help="profiles JSON path"),
    policy_path: str = typer.Option("ops/PREFLIGHT_POLICY.json", help="policy JSON path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Show current environment and the resolved preflight policy."""
    rep = _resolve_preflight_policy(
        work_queue_path="ops/WORK_QUEUE.md",
        patch_queue_path="ops/PATCH_QUEUE.md",
        stale_days=7,
        max_actionable=0,
        policy_path=policy_path,
        env_path=env_path,
        profiles_path=profiles_path,
    )
    if as_json:
        typer.echo(json.dumps(rep, indent=2))
    else:
        typer.echo(f"Environment: {rep['environment']}")
        typer.echo("Effective preflight policy:")
        typer.echo(f"- stale_days: {rep['effective']['stale_days']}")
        typer.echo(f"- max_actionable: {rep['effective']['max_actionable']}")

@app.command("capacity")
def capacity(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    env_path: str = typer.Option("ops/ENV.json", help="ENV.json path"),
    profiles_path: str = typer.Option("ops/PREFLIGHT_PROFILES.json", help="profiles JSON path"),
    policy_path: str = typer.Option("ops/PREFLIGHT_POLICY.json", help="policy JSON path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Show capacity stats and the effective caps for the current environment."""

    from .workqueue import parse_work_queue
    rows = parse_work_queue(work_queue_path)

    pol = _resolve_preflight_policy(
        work_queue_path=work_queue_path,
        patch_queue_path="ops/PATCH_QUEUE.md",
        stale_days=7,
        max_actionable=0,
        policy_path=policy_path,
        env_path=env_path,
        profiles_path=profiles_path,
    )
    eff = pol["effective"]
    snap = capacity_snapshot(rows)

    payload = {
        "environment": pol["environment"],
        "effective_caps": {
            "max_open_total": eff["max_open_total"],
            "max_doing_total": eff["max_doing_total"],
            "max_doing_per_assignee": eff["max_doing_per_assignee"],
            "max_open_per_client": eff["max_open_per_client"],
        },
        "status_counts": snap.status_counts,
        "open_per_client_top": snap.open_per_client[:10],
        "doing_per_assignee_top": snap.doing_per_assignee[:10],
    }

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"capacity: env={payload['environment']}")
    typer.echo("effective caps:")
    for k, v in payload["effective_caps"].items():
        typer.echo(f"- {k}: {v}")
    typer.echo("status counts:")
    for k, v in payload["status_counts"].items():
        typer.echo(f"- {k}: {v}")
    typer.echo("top open per client:")
    for cid, n in payload["open_per_client_top"]:
        label = cid if cid else "(missing)"
        typer.echo(f"- {label}: {n}")
    typer.echo("top doing per assignee:")
    for a, n in payload["doing_per_assignee_top"]:
        label = a if a else "(missing)"
        typer.echo(f"- {label}: {n}")


@app.command("flow")
def flow(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    env_path: str = typer.Option("ops/ENV.json", help="ENV.json path"),
    profiles_path: str = typer.Option("ops/PREFLIGHT_PROFILES.json", help="profiles JSON path"),
    policy_path: str = typer.Option("ops/PREFLIGHT_POLICY.json", help="policy JSON path"),
    window: str = typer.Option(None, help="Optional time window like '30d' (best-effort filter by created_utc)"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
    history_path: str = typer.Option("ops/METRICS_HISTORY.json", help="Metrics history append file"),
    append_history: bool = typer.Option(False, help="Append snapshot to history_path"),
):
    """Flow metrics: lead times + bottleneck warnings (operational cockpit)."""
    from .timeutils import window_to_since_iso, parse_utc

    pol = _resolve_preflight_policy(
        work_queue_path=work_queue_path,
        patch_queue_path="ops/PATCH_QUEUE.md",
        stale_days=7,
        max_actionable=0,
        policy_path=policy_path,
        env_path=env_path,
        profiles_path=profiles_path,
    )
    env = pol["environment"]

    from .workqueue import parse_work_queue
    rows = parse_work_queue(work_queue_path)

    now = now_utc_iso()
    # best-effort window filtering by created_utc
    since = window_to_since_iso(window)
    if since:
        since_dt = parse_utc(since)
        def _keep(r):
            try:
                return parse_utc(r.created_utc) >= since_dt
            except Exception:
                return True
        rows = [r for r in rows if _keep(r)]

    snap = flow_snapshot(rows, now_utc=now)
    warns = bottleneck_flags(
        rows,
        now_utc=now,
        open_age_warn_days=7,
        doing_age_warn_days=3,
        per_assignee_overload=pol["effective"].get("max_doing_per_assignee", 3),
        per_client_backlog=pol["effective"].get("max_open_per_client", 10),
    )

    payload = {
        "environment": env,
        "now_utc": now,
        "window": window,
        "flow": snap,
        "warnings": warns,
    }

    if append_history:
        p = Path(history_path)
        if p.exists():
            try:
                hist = json.loads(p.read_text(encoding="utf-8"))
                if not isinstance(hist, list):
                    hist = []
            except Exception:
                hist = []
        else:
            hist = []
        hist.append(payload)
        p.write_text(json.dumps(hist, indent=2) + "\n", encoding="utf-8")

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    def _fmt(v):
        return "n/a" if v is None else f"{v:.2f}"

    typer.echo(f"flow: env={env} now={now}" + (f" window={window}" if window else ""))
    for k in ("cycle_days", "queue_days", "exec_days"):
        m = payload["flow"][k]
        typer.echo(f"{k}: mean={_fmt(m['mean'])} median={_fmt(m['median'])} p90={_fmt(m['p90'])} n={m['n']}")
    typer.echo(f"age_open_days: mean={_fmt(payload['flow']['age_open_days']['mean'])} p90={_fmt(payload['flow']['age_open_days']['p90'])}")
    typer.echo(f"age_doing_days: mean={_fmt(payload['flow']['age_doing_days']['mean'])} p90={_fmt(payload['flow']['age_doing_days']['p90'])}")

    if warns:
        typer.echo("warnings:")
        for w in warns[:10]:
            kind = w.get("kind")
            if kind in ("assignee_overload", "client_backlog"):
                label = w.get("assignee") or w.get("client_id")
                typer.echo(f"- {kind}: {label} count={w.get('count')} threshold={w.get('threshold')}")
            elif kind in ("open_items_old", "doing_items_old"):
                typer.echo(f"- {kind}: count={w.get('count')} threshold_days={w.get('threshold_days')}")
            else:
                typer.echo(f"- {kind}: {w}")


@app.command("sla")
def sla(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    sla_policy_path: str = typer.Option("ops/SLA_POLICY.json", help="SLA policy JSON path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """SLA report: breaches for open/doing aging."""

    from .workqueue import parse_work_queue
    rows = parse_work_queue(work_queue_path)

    now = now_utc_iso()
    pol = _load_sla_policy(sla_policy_path)
    breaches = sla_breaches(
        rows,
        now_utc=now,
        open_sla_days=pol["open_sla_days"],
        doing_sla_days=pol["doing_sla_days"],
    )

    payload = {
        "now_utc": now,
        "policy": pol,
        "breaches": breaches,
        "breach_count": len(breaches),
    }

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"sla: now={now} open_sla_days={pol['open_sla_days']} doing_sla_days={pol['doing_sla_days']}")
    typer.echo(f"breaches: {len(breaches)}")
    for b in breaches[:20]:
        typer.echo(f"- {b['kind']}: {b['work_id']} age_days={b['age_days']} threshold={b['threshold_days']} title={b.get('title','')}")


@app.command("sla-plan")
def sla_plan(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    sla_policy_path: str = typer.Option("ops/SLA_POLICY.json", help="SLA policy JSON path"),
    out_path: str = typer.Option("ops/SLA_PATCH_LIST.md", help="Output markdown path"),
    write_file: bool = typer.Option(True, help="Write out_path (otherwise print to stdout)"),
    top_n: int = typer.Option(25, help="Max breaches to include"),
):
    """Generate an SLA remediation list (prioritized) as Markdown."""
    from .workqueue import parse_work_queue

    rows = parse_work_queue(work_queue_path)
    now = now_utc_iso()
    pol = _load_sla_policy(sla_policy_path)
    breaches = sla_breaches(
        rows,
        now_utc=now,
        open_sla_days=pol["open_sla_days"],
        doing_sla_days=pol["doing_sla_days"],
    )

    # prioritize: doing breaches first (execution blocked), then open; higher age first
    def _prio(b):
        kind = b.get("kind", "")
        tier = 0 if kind == "doing_sla_breach" else 1
        return (tier, -float(b.get("age_days", 0)), b.get("work_id", ""))

    breaches = sorted(breaches, key=_prio)[:max(0, int(top_n))]

    md = []
    md.append("# SLA Patch List")
    md.append("")
    md.append(f"- generated_utc: `{now}`")
    md.append(f"- policy: open_sla_days={pol['open_sla_days']} doing_sla_days={pol['doing_sla_days']} block_on_breach={pol.get('block_on_breach')}")
    md.append(f"- breaches_included: {len(breaches)}")
    md.append("")
    md.append("## Prioritized breaches")
    md.append("")
    md.append("| priority | kind | work_id | client_id | assignee | age_days | threshold_days | title | recommended_action |")
    md.append("|---:|---|---|---|---|---:|---:|---|---|")

    for i, b in enumerate(breaches, start=1):
        kind = b.get("kind", "")
        rec = "ship fix or de-scope" if kind == "doing_sla_breach" else "re-triage / schedule"
        md.append(f"| {i} | {kind} | {b.get('work_id','')} | {b.get('client_id','')} | {b.get('assignee','')} | {b.get('age_days','')} | {b.get('threshold_days','')} | {b.get('title','')} | {rec} |")

    md.append("")
    md.append("## Notes")
    md.append("")
    md.append("- Treat this file as an *actionable remediation list*; convert top items into PATCH_QUEUE entries if needed.")
    md.append("- For recurring breaches, tighten capacity caps or reduce WIP (max_doing_per_assignee).")
    md.append("")

    content = "\n".join(md) + "\n"

    if write_file:
        Path(out_path).write_text(content, encoding="utf-8")
        typer.echo(f"wrote {out_path} ({len(breaches)} breaches)")
    else:
        typer.echo(content)


@app.command("sla-to-patch-queue")
def sla_to_patch_queue(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    sla_policy_path: str = typer.Option("ops/SLA_POLICY.json", help="SLA policy JSON path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    top_n: int = typer.Option(10, help="Max breaches to emit"),
    dry_run: bool = typer.Option(False, help="Print planned sections, do not modify file"),
):
    """Emit SLA breaches as deterministic PATCH_QUEUE sections (append-only)."""
    from .workqueue import parse_work_queue

    rows = parse_work_queue(work_queue_path)
    now = now_utc_iso()
    pol = _load_sla_policy(sla_policy_path)

    breaches = sla_breaches(
        rows,
        now_utc=now,
        open_sla_days=pol["open_sla_days"],
        doing_sla_days=pol["doing_sla_days"],
    )

    def _prio(b):
        kind = b.get("kind", "")
        tier = 0 if kind == "doing_sla_breach" else 1
        return (tier, -float(b.get("age_days", 0)), b.get("work_id", ""))

    breaches = sorted(breaches, key=_prio)[:max(0, int(top_n))]

    pq = Path(patch_queue_path).read_text(encoding="utf-8") if Path(patch_queue_path).exists() else ""

    emitted = []
    for b in breaches:
        work_id = b.get("work_id", "")
        kind = b.get("kind", "")
        h = hashlib.sha1(f"{work_id}|{kind}".encode("utf-8")).hexdigest()[:8]
        qid = f"Q-SLA-{h}"
        if qid in pq:
            continue

        title = (b.get("title") or "").strip()
        header = f"## {qid} — SLA: {title or work_id}"
        status = "⬜ planned"
        rec = "Ship fix / de-scope immediately (execution blocking)" if kind == "doing_sla_breach" else "Re-triage & schedule (queue health)"
        section = []
        section.append(header)
        section.append(status)
        section.append("")
        section.append(f"**Generated:** {now}")
        section.append(f"**Source:** work_id={work_id} kind={kind} client_id={b.get('client_id', '')} age_days={b.get('age_days')} threshold_days={b.get('threshold_days')}")
        section.append("")
        section.append("**Deliverables**")
        section.append(f"- {rec}")
        section.append("- Add a concrete patch plan + acceptance criteria")
        section.append("- Update WORK_QUEUE status once started/done")
        section.append("")
        section.append("**Depends on**")
        section.append("- none")
        section.append("")
        section.append("---")
        section.append("")
        emitted.append("\n".join(section))

    if dry_run:
        typer.echo("\n".join(emitted) if emitted else "(no new SLA patches to emit)")
        return

    if not emitted:
        typer.echo("no new SLA patches (all already present)")
        return

    Path(patch_queue_path).write_text(pq + "\n" + "\n".join(emitted), encoding="utf-8")
    typer.echo(f"appended {len(emitted)} SLA patches to {patch_queue_path}")




@app.command("sla-autopromote")
def sla_autopromote(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    sla_policy_path: str = typer.Option("ops/SLA_POLICY.json", help="SLA policy JSON path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    top_n: int = typer.Option(10, help="Max SLA breaches to process"),
    max_doing_per_assignee: int = typer.Option(2, help="Cap for DOING items per assignee (excess routed to fallback)"),
    fallback_assignee: str = typer.Option("unassigned", help="Fallback assignee if cap exceeded / missing assignee"),
    dry_run: bool = typer.Option(False, help="Print planned changes, do not modify files"),
):
    """End-to-end: SLA breaches -> PATCH_QUEUE (Q-SLA-*) -> WORK_QUEUE rows (open).

    - Idempotent: Q-SLA-* patch_id is deterministic from (work_id, kind).
    - Promotion is idempotent: work_id deterministic from patch_id; WORK_QUEUE dedups by work_id.
    - Assignment: prefers breach assignee, but enforces DOING cap; overflow goes to fallback_assignee.
    """
    from .workqueue import parse_work_queue, append_work_queue, WorkItem
    from .patchqueue import parse_patch_queue, filter_items

    rows = parse_work_queue(work_queue_path)
    now = now_utc_iso()
    pol = _load_sla_policy(sla_policy_path)

    breaches = sla_breaches(
        rows,
        now_utc=now,
        open_sla_days=pol["open_sla_days"],
        doing_sla_days=pol["doing_sla_days"],
    )

    def _prio(b):
        kind = b.get("kind", "")
        tier = 0 if kind == "doing_sla_breach" else 1
        return (tier, -float(b.get("age_days", 0)), b.get("work_id", ""))

    breaches = sorted(breaches, key=_prio)[:max(0, int(top_n))]

    # current DOING counts per assignee
    doing_counts = {}
    for r in rows:
        if (r.status or "").strip().lower() == "doing":
            who = (r.assignee or "").strip() or fallback_assignee
            doing_counts[who] = doing_counts.get(who, 0) + 1

    pq_path = Path(patch_queue_path)
    pq_text = pq_path.read_text(encoding="utf-8") if pq_path.exists() else ""
    emitted_sections = []

    planned_patch_ids = []
    breach_by_patch_id = {}

    for b in breaches:
        work_id = b.get("work_id", "")
        kind = b.get("kind", "")
        client_id = (b.get("client_id") or "").strip()
        assignee = (b.get("assignee") or "").strip() or fallback_assignee

        h = hashlib.sha1(f"{work_id}|{kind}".encode("utf-8")).hexdigest()[:8]
        patch_id = f"Q-SLA-{h}"
        planned_patch_ids.append(patch_id)
        breach_by_patch_id[patch_id] = b

        if patch_id in pq_text:
            continue

        title = (b.get("title") or "").strip()
        header = f"## {patch_id} — SLA: {title or work_id}"
        status = "⬜ planned"
        rec = "Ship fix / de-scope immediately (execution blocking)" if kind == "doing_sla_breach" else "Re-triage & schedule (queue health)"
        section = []
        section.append(header)
        section.append(status)
        section.append("")
        section.append(f"**Generated:** {now}")
        section.append(f"**Source:** work_id={work_id} kind={kind} client_id={client_id} age_days={b.get('age_days')} threshold_days={b.get('threshold_days')}")
        section.append("")
        section.append("**Deliverables**")
        section.append(f"- {rec}")
        section.append("- Add a concrete patch plan + acceptance criteria")
        section.append("- Update WORK_QUEUE status once started/done")
        section.append("")
        section.append("**Depends on**")
        section.append("- none")
        section.append("")
        section.append("---")
        section.append("")
        emitted_sections.append("\n".join(section))

    # Dry-run printing
    if dry_run:
        typer.echo("=== SLA patches to append ===")
        typer.echo("\n".join(emitted_sections) if emitted_sections else "(none)")
        typer.echo("=== WORK rows to append ===")
        # compute what would be promoted (based on patch queue + emitted)
        tmp_pq = pq_text + ("\n" + "\n".join(emitted_sections) if emitted_sections else "")
        # naive parse by writing to tmp file
        tmp_path = pq_path.parent / (pq_path.name + ".tmp_dry_run")
        tmp_path.write_text(tmp_pq, encoding="utf-8")
        items = parse_patch_queue(str(tmp_path))
        try:
            planned = [p for p in filter_items(items, status_prefix="⬜") if p.patch_id in planned_patch_ids]
            existing = parse_work_queue(work_queue_path)
            existing_patch_ids = {r.patch_id for r in existing}
            for p in planned:
                if p.patch_id in existing_patch_ids:
                    continue
                b = breach_by_patch_id.get(p.patch_id, {})
                who = (b.get("assignee") or "").strip() or fallback_assignee
                if max_doing_per_assignee > 0 and doing_counts.get(who, 0) >= int(max_doing_per_assignee):
                    who = fallback_assignee
                wid = "W-" + hashlib.sha1(p.patch_id.encode("utf-8")).hexdigest()[:10]
                typer.echo(f"| {wid} | {p.patch_id} | {p.client_id or ''} | open | {who} | {now} |  |  | {p.title} | auto: sla-autopromote |")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return

    # Write patches first (append-only)
    if emitted_sections:
        pq_path.write_text(pq_text + "\n" + "\n".join(emitted_sections), encoding="utf-8")
        pq_text = pq_path.read_text(encoding="utf-8")

    # Promote Q-SLA planned items into WORK_QUEUE
    patches = parse_patch_queue(patch_queue_path)
    planned = [p for p in filter_items(patches, status_prefix="⬜") if p.patch_id in planned_patch_ids]

    existing = parse_work_queue(work_queue_path)
    existing_patch_ids = {r.patch_id for r in existing}

    promoted = 0
    for p in planned:
        if p.patch_id in existing_patch_ids:
            continue

        b = breach_by_patch_id.get(p.patch_id, {})
        who = (b.get("assignee") or "").strip() or fallback_assignee
        if max_doing_per_assignee > 0 and doing_counts.get(who, 0) >= int(max_doing_per_assignee):
            who = fallback_assignee

        wid = "W-" + hashlib.sha1(p.patch_id.encode("utf-8")).hexdigest()[:10]
        item = WorkItem(
            work_id=wid,
            patch_id=p.patch_id,
            client_id=p.client_id or "",
            status="open",
            assignee=who,
            created_utc=now,
            started_utc=None,
            done_utc=None,
            title=p.title,
            notes="auto: sla-autopromote",
            link_hint="",
        )
        append_work_queue(work_queue_path, item)
        promoted += 1

    typer.echo(f"sla-autopromote: appended {len(emitted_sections)} patches; promoted {promoted} work rows")
@app.command("patch-to-work")
def patch_to_work(
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    status_prefix: str = typer.Option("⬜", help="Select patches whose status line starts with this prefix"),
    top_n: int = typer.Option(10, help="Max patches to promote"),
    assignee: str = typer.Option("unassigned", help="Assignee to set on created work items"),
    dry_run: bool = typer.Option(False, help="Print planned table rows, do not modify file"),
):
    """Promote PATCH_QUEUE items into WORK_QUEUE rows (append-only, idempotent)."""
    from .patchqueue import parse_patch_queue, filter_items
    from .workqueue import parse_work_queue

    patches = parse_patch_queue(patch_queue_path)
    patches = filter_items(patches, status_prefix=status_prefix)[:max(0, int(top_n))]

    existing = parse_work_queue(work_queue_path)
    existing_patch_ids = {r.patch_id for r in existing}

    now = now_utc_iso()

    rows_to_add = []
    for p in patches:
        if p.patch_id in existing_patch_ids:
            continue
        # deterministic work_id from patch_id
        h = hashlib.sha1(p.patch_id.encode("utf-8")).hexdigest()[:10]
        work_id = f"W-{h}"
        title = p.title
        client_id = p.client_id or ""
        row = {
            "work_id": work_id,
            "patch_id": p.patch_id,
            "client_id": client_id,
            "status": "open",
            "assignee": assignee,
            "created_utc": now,
            "started_utc": "",
            "done_utc": "",
            "title": title,
            "notes": "",
        }
        rows_to_add.append(row)

    if dry_run:
        for r in rows_to_add:
            typer.echo(f"| {r['work_id']} | {r['patch_id']} | {r['client_id']} | {r['status']} | {r['assignee']} | {r['created_utc']} |  |  | {r['title']} | {r['notes']} |")
        if not rows_to_add:
            typer.echo("(no new work rows to add)")
        return

    if not rows_to_add:
        typer.echo("no new work rows (all patch_ids already present)")
        return

    # Append rows to WORK_QUEUE.md table; if missing, initialize.
    wqp = Path(work_queue_path)
    if not wqp.exists():
        wqp.write_text(
            "## Work Queue\n\n"
            "| work_id | patch_id | client_id | status | assignee | created_utc | started_utc | done_utc | title | notes |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )

    wtxt = wqp.read_text(encoding="utf-8")
    lines = wtxt.splitlines()

    # find end of table (last line that starts with '|')
    table_end = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("|"):
            table_end = i

    out_lines = lines[:table_end+1]
    for r in rows_to_add:
        out_lines.append(f"| {r['work_id']} | {r['patch_id']} | {r['client_id']} | {r['status']} | {r['assignee']} | {r['created_utc']} |  |  | {r['title']} | {r['notes']} |")
    out_lines.extend(lines[table_end+1:])

    wqp.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    typer.echo(f"appended {len(rows_to_add)} work rows to {work_queue_path}")


@app.command("preflight")
def preflight(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    policy_path: str = typer.Option("ops/PREFLIGHT_POLICY.json", help="JSON policy with stale_days/max_actionable"),
    env_path: str = typer.Option("ops/ENV.json", help="ENV.json path (dev/staging/prod)"),
    profiles_path: str = typer.Option("ops/PREFLIGHT_PROFILES.json", help="Profile policies by environment"),
    stale_days: int = typer.Option(7, help="Stale threshold in days (overrides config when set)"),
    max_actionable: int = typer.Option(0, help="Fail if actionable issues > this number (overrides config when set)"),
    sla_policy_path: str = typer.Option("ops/SLA_POLICY.json", help="SLA policy JSON path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Preflight gate for operators/CI.

    Policy resolution: CLI > ENV profile > policy file > defaults.
    Exits code 2 if actionable issues exceed threshold.
    """
    pol = _resolve_preflight_policy(
        work_queue_path=work_queue_path,
        patch_queue_path=patch_queue_path,
        stale_days=stale_days,
        max_actionable=max_actionable,
        policy_path=policy_path,
        env_path=env_path,
        profiles_path=profiles_path,
    )
    eff = pol["effective"]

    rep = _compute_preflight_report(work_queue_path, patch_queue_path, stale_days=eff["stale_days"])
    from .workqueue import parse_work_queue
    rows = parse_work_queue(work_queue_path)
    now_utc = now_utc_iso()
    # capacity cap checks (adds actionable issues)
    cap = rep.get("capacity", {})
    st = cap.get("status_counts", {})
    open_total = int(cap.get("open_total", st.get("open", 0) if isinstance(st, dict) else 0))
    doing_total = int(cap.get("doing_total", st.get("doing", 0) if isinstance(st, dict) else 0))

    if open_total > eff["max_open_total"]:
        rep["actionable"].append({
            "issue": "cap_open_total_exceeded",
            "work_id": "",
            "patch_id": "",
            "status": f"open_total={open_total} > cap={eff['max_open_total']}"
        })

    if doing_total > eff["max_doing_total"]:
        rep["actionable"].append({
            "issue": "cap_doing_total_exceeded",
            "work_id": "",
            "patch_id": "",
            "status": f"doing_total={doing_total} > cap={eff['max_doing_total']}"
        })

    # per-assignee doing cap
    for assignee, n in cap.get("doing_per_assignee", [])[:50]:
        if assignee and int(n) > eff["max_doing_per_assignee"]:
            rep["actionable"].append({
                "issue": "cap_doing_per_assignee_exceeded",
                "work_id": "",
                "patch_id": "",
                "status": f"{assignee}: {n} > cap={eff['max_doing_per_assignee']}"
            })

    # per-client open cap
    for client_id, n in cap.get("open_per_client", [])[:50]:
        if client_id and int(n) > eff["max_open_per_client"]:
            rep["actionable"].append({
                "issue": "cap_open_per_client_exceeded",
                "work_id": "",
                "patch_id": "",
                "status": f"{client_id}: {n} > cap={eff['max_open_per_client']}"
            })
    # SLA evaluation (open/doing aging)
    sla_pol = _load_sla_policy(sla_policy_path)
    breaches = sla_breaches(
        rows,
        now_utc=now_utc,
        open_sla_days=sla_pol["open_sla_days"],
        doing_sla_days=sla_pol["doing_sla_days"],
    )
    rep["sla"] = {"policy": sla_pol, "breach_count": len(breaches), "breaches": breaches[:50]}
    if breaches and sla_pol.get("block_on_breach"):
        rep["actionable"].append({
            "issue": "sla_breach_blocking",
            "work_id": "",
            "patch_id": "",
            "status": f"breaches={len(breaches)}"
        })

    out = {**rep, "policy": pol}

    if as_json:
        out["actionable"] = out["actionable"][:50]
        typer.echo(json.dumps(out, indent=2))
    else:
        c = rep["counts"]
        b = rep["backfill"]
        typer.echo("preflight:")
        typer.echo(f"- env: {pol['environment']}")
        typer.echo(f"- policy: stale_days={eff['stale_days']} max_actionable={eff['max_actionable']}")
        typer.echo(f"- caps: open_total<={eff['max_open_total']} doing_total<={eff['max_doing_total']} doing_per_assignee<={eff['max_doing_per_assignee']} open_per_client<={eff['max_open_per_client']}")
        warns = rep.get('warnings', [])
        if warns:
            typer.echo(f"- warnings (non-blocking): {len(warns)} (run `ae flow` for details)")
        sla_rep = rep.get('sla', {})
        if sla_rep.get('breach_count', 0):
            typer.echo(f"- sla breaches: {sla_rep.get('breach_count')} (run `ae sla`)")
        typer.echo(f"- backfill: scanned={b['scanned']} updated={b['updated']} missing_after={b['missing_after']}")
        typer.echo(
            f"- counts: total={c['total']} missing_client_id={c['missing_client_id']} "
            f"bad_status={c['bad_status']} blocked_no_reason={c['blocked_no_reason']} "
            f"stale(>{eff['stale_days']}d)={c['stale']} actionable={c['actionable']}"
        )
        if rep["actionable"]:
            typer.echo("actionable (top):")
            for a in rep["actionable"][:15]:
                extra = a.get("status") or ""
                typer.echo(f"- {a['issue']} | {a['work_id']} | {a['patch_id']} {extra}".rstrip())

    if len(rep["actionable"]) > eff["max_actionable"]:
        raise typer.Exit(code=2)


@app.command("ops-report")
def ops_report(
    last: int = typer.Option(30, help="Window size in days"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Compute operational metrics for the last N days."""
    from .workqueue_reader import read_work_queue
    from .metrics import report

    rows = read_work_queue(work_queue_path)
    payload = report(rows, days=last)

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"window_days: {payload['window_days']}")
    typer.echo(f"window_total: {payload['window_total']}")
    typer.echo(f"done: {payload['done']}")
    typer.echo(f"blocked: {payload['blocked']} (rate={round(payload['blocked_rate']*100, 2)}%)")
    if payload["avg_cycle_time_days"] is not None:
        typer.echo(f"avg_cycle_time_days: {round(payload['avg_cycle_time_days'], 2)}")
    else:
        typer.echo("avg_cycle_time_days: n/a")
    if payload["avg_start_to_done_days"] is not None:
        typer.echo(f"avg_start_to_done_days: {round(payload['avg_start_to_done_days'], 2)}")
    else:
        typer.echo("avg_start_to_done_days: n/a")
    if payload["top_blocked_reasons"]:
        typer.echo("top_blocked_reasons:")
        for r in payload["top_blocked_reasons"]:
            typer.echo(f"- {r['count']} × {r['reason']}")


@app.command("work-stale")
def work_stale(
    days: int = typer.Option(7, help="Show work items older than this many days"),
    status: Optional[str] = typer.Option(None, help="Optional status filter"),
    assignee: Optional[str] = typer.Option(None, help="Optional assignee filter"),
    limit: int = typer.Option(50, help="Max items"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Find stale work items by created_utc age."""
    from .workqueue_reader import read_work_queue, filter_work
    from .metrics import stale_work

    rows = filter_work(read_work_queue(work_queue_path), status=status, assignee=assignee)
    stale = stale_work(rows, days=days)[:max(0, limit)]

    if as_json:
        typer.echo(json.dumps([s.__dict__ for s in stale], indent=2))
        return

    typer.echo("work_id | status | assignee | age_days | title")
    typer.echo("------|------|---------|---------|------")
    for s in stale:
        typer.echo(f"{s.work_id} | {s.status} | {s.assignee} | {round(s.age_days, 2)} | {s.title}")



@app.command("client-status")
def client_status(
    client_id: str = typer.Option(..., help="Client identifier (slug)"),
    last: int = typer.Option(30, help="Reporting window in days (for ops-report sub-metrics)"),
    stale_days: int = typer.Option(7, help="Stale threshold in days"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Client-level operational snapshot: counts, stale work, blockers, latest autoplan patch."""
    from collections import Counter
    from .workqueue_reader import read_work_queue
    from .metrics import stale_work, report
    from .patchqueue_reader import latest_patch_for_client

    rows = read_work_queue(work_queue_path)

    # client-specific work: explicit client_id column
    client_rows = [r for r in rows if r.client_id.lower() == client_id.lower()]

    # Back-compat: if client_id column isn't populated yet, fall back to substring match
    if not client_rows:
        cid = client_id.lower()
        for r in rows:
            hay = (r.title + " " + (r.notes or "") + " " + r.patch_id + " " + r.work_id).lower()
            if cid in hay:
                client_rows.append(r)


    status_counts = Counter([r.status.lower() for r in client_rows])

    # blockers
    reasons = []
    for r in client_rows:
        if r.status.lower() == "blocked" and "BLOCKED:" in (r.notes or ""):
            idx = r.notes.find("BLOCKED:")
            reasons.append(r.notes[idx + len("BLOCKED:"):].strip())
    top_reasons = Counter(reasons).most_common(5)

    stale = stale_work(client_rows, days=stale_days)[:20]
    metrics = report(client_rows, days=last)

    latest_patch = latest_patch_for_client(patch_queue_path, client_id)
    latest_patch_id = latest_patch.patch_id if latest_patch else None

    payload = {
        "client_id": client_id,
        "work_total": len(client_rows),
        "status_counts": dict(status_counts),
        "top_blocked_reasons": [{"reason": k, "count": v} for k, v in top_reasons],
        "stale_days": stale_days,
        "stale": [s.__dict__ for s in stale],
        "metrics": metrics,
        "latest_autoplan_patch_id": latest_patch_id,
    }

    if as_json:
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"client_id: {client_id}")
    typer.echo(f"latest_autoplan_patch_id: {latest_patch_id or 'n/a'}")
    typer.echo(f"work_total: {payload['work_total']}")
    typer.echo(f"status_counts: {payload['status_counts']}")
    if payload["top_blocked_reasons"]:
        typer.echo("top_blocked_reasons:")
        for r in payload["top_blocked_reasons"]:
            typer.echo(f"- {r['count']} × {r['reason']}")
    if payload["stale"]:
        typer.echo(f"stale (>{stale_days}d):")
        for s in payload["stale"]:
            typer.echo(f"- {s['work_id']} | {s['status']} | {round(s['age_days'],2)}d | {s['title']}")
    typer.echo(f"metrics(last={last}d): done={payload['metrics']['done']} blocked={payload['metrics']['blocked']} rate={round(payload['metrics']['blocked_rate']*100,2)}%")


@app.command("work-search")
def work_search(
    q: str = typer.Option(..., help="Search query (case-insensitive) across title + notes"),
    status: Optional[str] = typer.Option(None, help="Optional status filter"),
    assignee: Optional[str] = typer.Option(None, help="Optional assignee filter"),
    limit: int = typer.Option(50, help="Max rows"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Search work items by substring match in title/notes."""
    from .workqueue_reader import read_work_queue, filter_work

    rows = filter_work(read_work_queue(work_queue_path), status=status, assignee=assignee)
    qq = q.lower().strip()
    hits = []
    for r in rows:
        hay = (r.title + " " + (r.notes or "")).lower()
        if qq in hay:
            hits.append(r)
    hits = hits[:max(0, limit)]

    if as_json:
        typer.echo(json.dumps([h.__dict__ for h in hits], indent=2))
        return

    typer.echo("work_id | status | assignee | title")
    typer.echo("------|------|---------|------")
    for r in hits:
        typer.echo(f"{r.work_id} | {r.status} | {r.assignee} | {r.title}")


@app.command("work-done")
def work_done(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    notes: str = typer.Option("", help="Completion notes (short)"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Mark a work item as done and stamp done_utc; optionally store notes."""
    from .workqueue import complete_work, append_log_horizon

    ok = complete_work(work_queue_path, work_id, notes=notes)
    if not ok:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    msg = f"- work_done: `{work_id}`\n- status: **done**"
    if notes:
        msg += f"\n- notes: {notes}"
    append_log_horizon(log_path, msg)
    typer.echo(f"Done {work_id}")



@app.command("work-backfill-client-ids")
def work_backfill_client_ids(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    as_json: bool = typer.Option(False, help="Emit JSON"),
):
    """Backfill missing client_id values in WORK_QUEUE from PATCH_QUEUE."""
    from .workqueue import backfill_client_ids
    rep = backfill_client_ids(work_queue_path, patch_queue_path)

    if as_json:
        typer.echo(json.dumps(rep, indent=2))
        return

    typer.echo(f"scanned: {rep['scanned']}")
    typer.echo(f"updated: {rep['updated']}")
    typer.echo(f"missing_after: {rep['missing_after']}")


@app.command()
def validate_page(
    db: str = typer.Option(...),
    page_id: str = typer.Option(...),
):
    ok, errors = service.validate_page(db, page_id)
    if ok:
        typer.echo("OK: publish readiness passed")
    else:
        typer.echo("FAIL: publish readiness failed")
        for e in errors:
            typer.echo(f"- {e}")
        raise typer.Exit(code=2)


@app.command("work-note")
def work_note(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    note: str = typer.Option(..., help="Note to append to the work item"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Append a note to a work item (keeps current status)."""
    from .workqueue import note_work, append_log_horizon

    ok = note_work(work_queue_path, work_id, note)
    if not ok:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    append_log_horizon(log_path, f"- work_note: `{work_id}`\n- note: {note}")
    typer.echo(f"Noted {work_id}")


@app.command("work-block")
def work_block(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    reason: str = typer.Option(..., help="Why work is blocked"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Mark a work item as blocked and record reason."""
    from .workqueue import block_work, append_log_horizon

    ok = block_work(work_queue_path, work_id, reason)
    if not ok:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    append_log_horizon(log_path, f"- work_block: `{work_id}`\n- reason: {reason}")
    typer.echo(f"Blocked {work_id}")


@app.command()
def publish_page(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_id: str = typer.Option(..., help="Page ID"),
    notes: Optional[str] = typer.Option(None, help="Optional publish notes"),
    content_adapter: Optional[str] = typer.Option(None, "--content-adapter", help="Override content adapter (e.g. stub)"),
    publisher_adapter: Optional[str] = typer.Option(None, "--publisher-adapter", help="Override publisher adapter (local_file|framer_stub|tailwind_static|webflow_stub)"),
    analytics_adapter: Optional[str] = typer.Option(None, "--analytics-adapter", help="Override analytics adapter (db)"),
    publish_out_dir: Optional[str] = typer.Option(None, "--publish-out-dir", help="Override local_file output dir"),
    framer_out_dir: Optional[str] = typer.Option(None, "--framer-out-dir", help="Override framer_stub output dir"),
    static_out_dir: Optional[str] = typer.Option(None, "--static-out-dir", help="Override tailwind_static output dir"),
    webflow_out_dir: Optional[str] = typer.Option(None, "--webflow-out-dir", help="Override webflow_stub output dir"),
):
    override = {
        k: v
        for k, v in {
            "content": content_adapter,
            "publisher": publisher_adapter,
            "analytics": analytics_adapter,
            "publish_out_dir": publish_out_dir,
            "framer_out_dir": framer_out_dir,
            "static_out_dir": static_out_dir,
            "webflow_out_dir": webflow_out_dir,
        }.items()
        if v
    } or None

    ok, errors = service.publish_page(db, page_id, notes=notes, adapter_config_override=override)
    if ok:
        typer.echo("OK: page published (live)")
    else:
        typer.echo("FAIL: page not published")
        for e in errors:
            typer.echo(f"- {e}")
        raise typer.Exit(code=2)


@app.command("work-unblock")
def work_unblock(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    note: str = typer.Option("", help="Optional note (e.g., what unblocked it)"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Mark a work item as unblocked (status=open) and optionally record note."""
    from .workqueue import unblock_work, append_log_horizon

    ok = unblock_work(work_queue_path, work_id, note=note)
    if not ok:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    msg = f"- work_unblock: `{work_id}`\n- status: **open**"
    if note:
        msg += f"\n- note: {note}"
    append_log_horizon(log_path, msg)
    typer.echo(f"Unblocked {work_id}")


@app.command("work-resume")
def work_resume(
    work_id: str = typer.Option(..., help="Work ID like W-AP-xxxxxxxxxx"),
    note: str = typer.Option("", help="Optional note"),
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="LOG_HORIZON.md path"),
):
    """Resume execution (status=doing). If started_utc missing, it will be stamped."""
    from .workqueue import resume_work, append_log_horizon

    ok = resume_work(work_queue_path, work_id, note=note)
    if not ok:
        raise typer.BadParameter(f"work_id not found in {work_queue_path}: {work_id}")

    msg = f"- work_resume: `{work_id}`\n- status: **doing**"
    if note:
        msg += f"\n- note: {note}"
    append_log_horizon(log_path, msg)
    typer.echo(f"Resumed {work_id}")


@app.command()
def pause_page(
    db: str = typer.Option(...),
    page_id: str = typer.Option(...),
    notes: Optional[str] = typer.Option(None),
):
    service.pause_page(db, page_id, notes=notes)
    typer.echo("OK: page paused")

@app.command()
def log_change(
    db: str = typer.Option(...),
    page_id: str = typer.Option(...),
    changed_field: List[str] = typer.Option(..., help="Repeatable. Example: --changed-field hero_image --changed-field phone"),
    notes: Optional[str] = typer.Option(None),
):
    log = service.log_change(db, page_id, changed_fields=changed_field, notes=notes)
    typer.echo(f"OK: content version bumped to {log.content_version_after}")

@app.command()
def enqueue_work(
    db: str = typer.Option(...),
    type: WorkType = typer.Option(...),
    client_id: str = typer.Option(...),
    priority: Priority = typer.Option(Priority.normal),
    page_id: Optional[str] = typer.Option(None),
    acceptance: Optional[str] = typer.Option(None),
):
    item = service.enqueue_work(db, type, client_id, page_id, priority, acceptance)
    typer.echo(f"OK: work_item {item.work_item_id} ({item.type.value})")

@app.command()
def list_work(
    db: str = typer.Option(...),
    status: Optional[str] = typer.Option(None, help="Optional status filter, e.g. new, ready, in_progress"),
):
    items = repo.list_work(db, status=status)
    for it in items:
        typer.echo(f"{it.work_item_id} | {it.status.value:<11} | {it.priority.value:<6} | {it.type.value:<13} | client={it.client_id} page={it.page_id or '-'}")

@app.command()
def record_event(
    db: str = typer.Option(...),
    page_id: str = typer.Option(...),
    event_name: EventName = typer.Option(...),
    params_json: Optional[str] = typer.Option(None, help="JSON string of event params"),
):
    params = json.loads(params_json) if params_json else {}
    ev = service.record_event(db, page_id, event_name, params=params)
    typer.echo(f"OK: event {ev.event_name.value} recorded ({ev.event_id})")



@app.command()
def enqueue_bulk(
    db: str = typer.Option(...),
    action: str = typer.Option(..., help="validate|publish|pause"),
    mode: str = typer.Option("dry_run", help="dry_run|execute"),
    page_id: List[str] = typer.Option(..., help="Repeatable. Example: --page-id p1 --page-id p2"),
    notes: Optional[str] = typer.Option(None),
):
    import uuid as _uuid
    from .models import BulkOp
    bulk_id = f"bulk_{_uuid.uuid4().hex[:12]}"
    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action=action,
        selector_json={"page_ids": page_id},
        status="queued",
        notes=notes,
    )
    repo.insert_bulk_op(db, op)
    typer.echo(f"OK: bulk op queued {bulk_id} ({action}, {mode})")

@app.command()
def run_bulk(
    db: str = typer.Option(...),
    bulk_id: str = typer.Option(...),
):
    result = service.run_bulk_op(db, bulk_id)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def create_patch(
    patch_id: str = typer.Option(..., help="P-YYYYMMDD-####"),
    version: str = typer.Option(..., help="Semantic version, e.g. v0.1.2"),
    type: str = typer.Option(..., help="patch|feature|refactor|doc|hotfix"),
    summary: str = typer.Option(..., help="One-line summary of the patch"),
    repo_root: str = typer.Option(".", help="Repo root path for ops/patches storage"),
):
    from pathlib import Path
    from . import cadence
    meta = cadence.create_patch(Path(repo_root), patch_id, version, type, summary)
    typer.echo(json.dumps(meta.__dict__, indent=2))

@app.command()
def verify_release(
    patch_id: str = typer.Option(..., help="Existing patch id"),
    log_horizon_md: str = typer.Option(..., help="Path to LOG_HORIZON.md (append-only)"),
    artifact: List[str] = typer.Option([], help="Repeatable artifacts, e.g. --artifact acq_engine_v0_1_2.zip"),
    notes: Optional[str] = typer.Option(None),
    next: Optional[str] = typer.Option(None),
    repo_root: str = typer.Option(".", help="Repo root path for ops/releases storage"),
):
    from pathlib import Path
    from . import cadence
    res = cadence.verify_release(Path(repo_root), patch_id, Path(log_horizon_md), artifacts=artifact, notes=notes, next_=next)
    typer.echo(json.dumps(res, indent=2))
    if not res.get("ok"):
        raise typer.Exit(code=2)


@app.command()
def next_patch_id(
    repo_root: str = typer.Option(".", help="Repo root path for ops/patches"),
    date: Optional[str] = typer.Option(None, help="YYYYMMDD override; default UTC today"),
):
    from pathlib import Path
    from . import cadence
    pid = cadence.next_patch_id(Path(repo_root), date_yyyymmdd=date)
    typer.echo(pid)

@app.command()
def start_work(
    version: str = typer.Option(..., help="Semantic version, e.g. v0.1.3"),
    type: str = typer.Option(..., help="patch|feature|refactor|doc|hotfix"),
    summary: str = typer.Option(..., help="One-line summary"),
    patch_id: Optional[str] = typer.Option(None, help="Optional explicit P-YYYYMMDD-####"),
    repo_root: str = typer.Option(".", help="Repo root path"),
):
    from pathlib import Path
    from . import cadence
    meta = cadence.start_work(Path(repo_root), version=version, type_=type, summary=summary, patch_id=patch_id)
    typer.echo(json.dumps(meta.__dict__, indent=2))

@app.command()
def finish_work(
    patch_id: str = typer.Option(..., help="Existing patch id"),
    log_horizon_md: str = typer.Option(..., help="Path to LOG_HORIZON.md (append-only)"),
    artifact: List[str] = typer.Option([], help="Repeatable artifacts"),
    notes: Optional[str] = typer.Option(None),
    next: Optional[str] = typer.Option(None),
    repo_root: str = typer.Option(".", help="Repo root path"),
):
    from pathlib import Path
    from . import cadence
    res = cadence.finish_work(Path(repo_root), patch_id, Path(log_horizon_md), artifacts=artifact, notes=notes, next_=next)
    typer.echo(json.dumps(res, indent=2))
    if not res.get("ok"):
        raise typer.Exit(code=2)


@app.command()
def analytics_summary(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_id: str = typer.Option(..., help="Page ID"),
    content_adapter: Optional[str] = typer.Option(None, "--content-adapter", help="Override content adapter (e.g. stub)"),
    publisher_adapter: Optional[str] = typer.Option(None, "--publisher-adapter", help="Override publisher adapter (local_file|framer_stub|tailwind_static|webflow_stub)"),
    analytics_adapter: Optional[str] = typer.Option(None, "--analytics-adapter", help="Override analytics adapter (db)"),
    publish_out_dir: Optional[str] = typer.Option(None, "--publish-out-dir", help="Override local_file output dir"),
    framer_out_dir: Optional[str] = typer.Option(None, "--framer-out-dir", help="Override framer_stub output dir"),
    static_out_dir: Optional[str] = typer.Option(None, "--static-out-dir", help="Override tailwind_static output dir"),
    webflow_out_dir: Optional[str] = typer.Option(None, "--webflow-out-dir", help="Override webflow_stub output dir"),
):
    override = {
        k: v
        for k, v in {
            "content": content_adapter,
            "publisher": publisher_adapter,
            "analytics": analytics_adapter,
            "publish_out_dir": publish_out_dir,
            "framer_out_dir": framer_out_dir,
            "static_out_dir": static_out_dir,
            "webflow_out_dir": webflow_out_dir,
        }.items()
        if v
    } or None

    adapters = service.resolve_adapters(repo, override)
    page = repo.get_page(db, page_id)
    if not page:
        typer.echo(f"FAIL: page not found: {page_id}")
        raise typer.Exit(code=2)

    summary = adapters.analytics.get_page_summary(db, page_id)
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def bulk_publish(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_ids: Optional[str] = typer.Option(None, help="Comma-separated page ids. If omitted, uses selector."),
    page_status: Optional[str] = typer.Option(None, help="Select pages by status (draft|live|paused). Default=draft."),
    limit: int = typer.Option(200, help="Max pages when selecting by status"),
    execute: bool = typer.Option(False, "--execute", help="Execute publishes (default is dry-run validation only)"),
    force: bool = typer.Option(False, "--force", help="Re-publish even if page already live"),
    notes: Optional[str] = typer.Option(None, help="Notes for publish log / bulk op"),
    content_adapter: Optional[str] = typer.Option(None, "--content-adapter", help="Override content adapter (stub)"),
    publisher_adapter: Optional[str] = typer.Option(None, "--publisher-adapter", help="Override publisher adapter (local_file|framer_stub|tailwind_static|webflow_stub)"),
    analytics_adapter: Optional[str] = typer.Option(None, "--analytics-adapter", help="Override analytics adapter (db)"),
    publish_out_dir: Optional[str] = typer.Option(None, "--publish-out-dir", help="Override local_file output dir"),
    framer_out_dir: Optional[str] = typer.Option(None, "--framer-out-dir", help="Override framer_stub output dir"),
    static_out_dir: Optional[str] = typer.Option(None, "--static-out-dir", help="Override tailwind_static output dir"),
    webflow_out_dir: Optional[str] = typer.Option(None, "--webflow-out-dir", help="Override webflow_stub output dir"),
):
    """Run bulk publish (validate or execute) with idempotency + locking."""
    override = {
        k: v
        for k, v in {
            "content": content_adapter,
            "publisher": publisher_adapter,
            "analytics": analytics_adapter,
            "publish_out_dir": publish_out_dir,
            "framer_out_dir": framer_out_dir,
            "static_out_dir": static_out_dir,
            "webflow_out_dir": webflow_out_dir,
        }.items()
        if v
    } or None

    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None
    mode = "execute" if execute else "dry_run"
    op = service.run_bulk_publish(
        db,
        page_ids=ids,
        page_status=page_status,
        client_id=client_id,
        template_id=template_id,
        geo_city=geo_city,
        geo_country=geo_country,
        limit=limit,
        mode=mode,
        force=force,
        notes=notes,
        adapter_config_override=override,
    )
    counters = op.result_json.get("counters", {})
    typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} mode={op.mode}")
    typer.echo(json.dumps(counters, indent=2))


@app.command()
def kpi_report(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_id: str = typer.Option(..., help="Page ID"),
    impressions: Optional[int] = typer.Option(None, help="Ad impressions (optional placeholder input)"),
    clicks: Optional[int] = typer.Option(None, help="Ad clicks (optional placeholder input)"),
    spend: Optional[float] = typer.Option(None, help="Spend (optional placeholder input)"),
    revenue: Optional[float] = typer.Option(None, help="Revenue (optional placeholder input)"),
    since_iso: Optional[str] = typer.Option(None, "--since-iso", help="Sum ad_stats since this ISO timestamp (when no placeholders provided)"),
    platform: Optional[str] = typer.Option(None, help="Filter ad_stats by platform (meta|google|other)"),
    content_adapter: Optional[str] = typer.Option(None, "--content-adapter", help="Override content adapter (stub)"),
    publisher_adapter: Optional[str] = typer.Option(None, "--publisher-adapter", help="Override publisher adapter (local_file|framer_stub|tailwind_static|webflow_stub)"),
    analytics_adapter: Optional[str] = typer.Option(None, "--analytics-adapter", help="Override analytics adapter (db)"),
    publish_out_dir: Optional[str] = typer.Option(None, "--publish-out-dir", help="Override local_file output dir"),
    framer_out_dir: Optional[str] = typer.Option(None, "--framer-out-dir", help="Override framer_stub output dir"),
    static_out_dir: Optional[str] = typer.Option(None, "--static-out-dir", help="Override tailwind_static output dir"),
    webflow_out_dir: Optional[str] = typer.Option(None, "--webflow-out-dir", help="Override webflow_stub output dir"),
):
    override = {
        k: v
        for k, v in {
            "content": content_adapter,
            "publisher": publisher_adapter,
            "analytics": analytics_adapter,
            "publish_out_dir": publish_out_dir,
            "framer_out_dir": framer_out_dir,
            "static_out_dir": static_out_dir,
            "webflow_out_dir": webflow_out_dir,
        }.items()
        if v
    } or None
    rep = service.kpi_report(
        db,
        page_id,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        revenue=revenue,
        since_iso=since_iso,
        platform=platform,
        adapter_config_override=override,
    )
    typer.echo(json.dumps(rep, indent=2))

@app.command()
def export_kpis(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    out: str = typer.Option("exports/reports/kpis.json", help="Output path (json or csv)"),
    fmt: str = typer.Option("json", help="json|csv"),
    page_ids: Optional[str] = typer.Option(None, help="Comma-separated page ids. If omitted, uses selector."),
    page_status: Optional[str] = typer.Option(None, help="Select pages by status (draft|live|paused). Default=draft."),
    limit: int = typer.Option(200, help="Max pages when selecting by status"),
    impressions: Optional[int] = typer.Option(None, help="Ad impressions placeholder input"),
    clicks: Optional[int] = typer.Option(None, help="Ad clicks placeholder input"),
    spend: Optional[float] = typer.Option(None, help="Spend placeholder input"),
    revenue: Optional[float] = typer.Option(None, help="Revenue placeholder input"),
    since_iso: Optional[str] = typer.Option(None, "--since-iso", help="Sum ad_stats since this ISO timestamp (when no placeholders provided)"),
    platform: Optional[str] = typer.Option(None, help="Filter ad_stats by platform (meta|google|other)"),
    content_adapter: Optional[str] = typer.Option(None, "--content-adapter", help="Override content adapter (stub)"),
    publisher_adapter: Optional[str] = typer.Option(None, "--publisher-adapter", help="Override publisher adapter (local_file|framer_stub|tailwind_static|webflow_stub)"),
    analytics_adapter: Optional[str] = typer.Option(None, "--analytics-adapter", help="Override analytics adapter (db)"),
    publish_out_dir: Optional[str] = typer.Option(None, "--publish-out-dir", help="Override local_file output dir"),
    framer_out_dir: Optional[str] = typer.Option(None, "--framer-out-dir", help="Override framer_stub output dir"),
    static_out_dir: Optional[str] = typer.Option(None, "--static-out-dir", help="Override tailwind_static output dir"),
    webflow_out_dir: Optional[str] = typer.Option(None, "--webflow-out-dir", help="Override webflow_stub output dir"),
):
    override = {
        k: v
        for k, v in {
            "content": content_adapter,
            "publisher": publisher_adapter,
            "analytics": analytics_adapter,
            "publish_out_dir": publish_out_dir,
            "framer_out_dir": framer_out_dir,
            "static_out_dir": static_out_dir,
            "webflow_out_dir": webflow_out_dir,
        }.items()
        if v
    } or None

    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None
    out_path = service.export_kpis(
        db,
        out_path=out,
        fmt=fmt,
        page_ids=ids,
        page_status=page_status,
        limit=limit,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        revenue=revenue,
        since_iso=since_iso,
        platform=platform,
        adapter_config_override=override,
    )
    typer.echo(f"OK: exported to {out_path}")


@app.command()
def record_ad_stat(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_id: str = typer.Option(..., help="Page ID"),
    platform: str = typer.Option(..., help="meta|google|other"),
    impressions: Optional[int] = typer.Option(None, help="Impressions"),
    clicks: Optional[int] = typer.Option(None, help="Clicks"),
    spend: Optional[float] = typer.Option(None, help="Spend"),
    revenue: Optional[float] = typer.Option(None, help="Revenue"),
    timestamp_iso: Optional[str] = typer.Option(None, help="ISO timestamp (defaults to now)"),
    campaign_id: Optional[str] = typer.Option(None, help="Campaign id"),
    adset_id: Optional[str] = typer.Option(None, help="Adset id"),
    ad_id: Optional[str] = typer.Option(None, help="Ad id"),
):
    stat_id = service.record_ad_stat(
        db,
        page_id,
        platform=platform,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        revenue=revenue,
        campaign_id=campaign_id,
        adset_id=adset_id,
        ad_id=ad_id,
        timestamp_iso=timestamp_iso,
    )
    typer.echo(f"OK: recorded ad_stat {stat_id}")


@app.command()
def import_ad_stats_csv(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    csv_path: str = typer.Option(..., help="Path to normalized CSV file"),
    default_platform: Optional[str] = typer.Option(None, help="Default platform if CSV lacks platform"),
    default_page_id: Optional[str] = typer.Option(None, help="Default page_id if CSV lacks page_id"),
    timestamp_col: str = typer.Option("timestamp", help="Timestamp column name (default: timestamp)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse only, do not insert"),
):
    rep = service.import_ad_stats_csv(
        db,
        csv_path=csv_path,
        default_platform=default_platform,
        default_page_id=default_page_id,
        timestamp_col=timestamp_col,
        dry_run=dry_run,
    )
    typer.echo(json.dumps(rep, indent=2))


@app.command()
def import_meta_export_csv(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    csv_path: str = typer.Option(..., help="Meta export CSV path"),
    page_id: str = typer.Option(..., help="Default page_id to attach stats to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse only, do not insert"),
    aliases_path: str = typer.Option("ops/ad_platform_aliases.json", "--aliases-path", help="Path to alias registry JSON"),
):
    # aliases are loaded by service; this param is reserved for future explicit path support
    rep = service.import_meta_export_csv(db, csv_path=csv_path, default_page_id=page_id, aliases_path=aliases_path, dry_run=dry_run)
    typer.echo(json.dumps(rep, indent=2))

@app.command()
def import_google_ads_export_csv(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    csv_path: str = typer.Option(..., help="Google Ads export CSV path"),
    page_id: str = typer.Option(..., help="Default page_id to attach stats to"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse only, do not insert"),
    aliases_path: str = typer.Option("ops/ad_platform_aliases.json", "--aliases-path", help="Path to alias registry JSON"),
):
    # aliases are loaded by service; this param is reserved for future explicit path support
    rep = service.import_google_ads_export_csv(db, csv_path=csv_path, default_page_id=page_id, aliases_path=aliases_path, dry_run=dry_run)
    typer.echo(json.dumps(rep, indent=2))


@app.command()
def validate_aliases(
    aliases_path: str = typer.Option("ops/ad_platform_aliases.json", "--aliases-path", help="Path to alias registry JSON"),
):
    rep = service.validate_ad_platform_aliases(aliases_path)
    typer.echo(json.dumps(rep, indent=2))
    if not rep.get("ok", False):
        raise typer.Exit(code=2)


@app.command()
def bulk_validate(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_ids: Optional[str] = typer.Option(None, help="Comma-separated page ids. If omitted, uses selector."),
    page_status: Optional[str] = typer.Option(None, help="Select pages by status (draft|live|paused). Optional."),
    client_id: Optional[str] = typer.Option(None, "--client-id", help="Select pages by client_id"),
    template_id: Optional[str] = typer.Option(None, "--template-id", help="Select pages by template_id"),
    geo_city: Optional[str] = typer.Option(None, "--geo-city", help="Select pages by client geo_city"),
    geo_country: Optional[str] = typer.Option(None, "--geo-country", help="Select pages by client geo_country"),
    limit: int = typer.Option(200, help="Max pages when selecting by filters"),
    notes: Optional[str] = typer.Option(None, help="Notes for bulk op"),
):
    """Run bulk validate using selectors."""
    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None
    op = service.run_bulk_validate(
        db,
        page_ids=ids,
        page_status=page_status,
        client_id=client_id,
        template_id=template_id,
        geo_city=geo_city,
        geo_country=geo_country,
        limit=limit,
        mode="dry_run",
        notes=notes,
    )
    counters = op.result_json.get("counters", {})
    typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} action={op.action}")
    typer.echo(json.dumps(counters, indent=2))


@app.command()
def bulk_pause(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_ids: Optional[str] = typer.Option(None, help="Comma-separated page ids. If omitted, uses selector."),
    page_status: Optional[str] = typer.Option(None, help="Select pages by status (draft|live|paused). Optional."),
    client_id: Optional[str] = typer.Option(None, "--client-id", help="Select pages by client_id"),
    template_id: Optional[str] = typer.Option(None, "--template-id", help="Select pages by template_id"),
    geo_city: Optional[str] = typer.Option(None, "--geo-city", help="Select pages by client geo_city"),
    geo_country: Optional[str] = typer.Option(None, "--geo-country", help="Select pages by client geo_country"),
    limit: int = typer.Option(200, help="Max pages when selecting by filters"),
    execute: bool = typer.Option(False, "--execute", help="Execute pauses (default dry-run)"),
    notes: Optional[str] = typer.Option(None, help="Notes for bulk op"),
):
    """Run bulk pause (dry-run or execute) using selectors."""
    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None
    mode = "execute" if execute else "dry_run"
    op = service.run_bulk_pause(
        db,
        page_ids=ids,
        page_status=page_status,
        client_id=client_id,
        template_id=template_id,
        geo_city=geo_city,
        geo_country=geo_country,
        limit=limit,
        mode=mode,
        notes=notes,
    )
    counters = op.result_json.get("counters", {})
    typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} mode={op.mode} action={op.action}")
    typer.echo(json.dumps(counters, indent=2))


@app.command()
def bulk_run(
    action: str = typer.Option(..., "--action", help="Action: validate|pause|publish"),
    db: str = typer.Option(..., help="Path to sqlite db file"),
    page_ids: Optional[str] = typer.Option(None, help="Comma-separated page ids. If omitted, uses selector."),
    page_status: Optional[str] = typer.Option(None, help="Select pages by status (draft|live|paused). Optional."),
    client_id: Optional[str] = typer.Option(None, "--client-id", help="Select pages by client_id"),
    template_id: Optional[str] = typer.Option(None, "--template-id", help="Select pages by template_id"),
    geo_city: Optional[str] = typer.Option(None, "--geo-city", help="Select pages by client geo_city"),
    geo_country: Optional[str] = typer.Option(None, "--geo-country", help="Select pages by client geo_country"),
    limit: int = typer.Option(200, help="Max pages when selecting by filters"),
    execute: bool = typer.Option(False, "--execute", help="Execute (for pause/publish). Default dry-run."),
    force: bool = typer.Option(False, "--force", help="Force publish even if paused/validation fails (publish only)"),
    adapter_override_json: Optional[str] = typer.Option(None, "--adapter-override-json", help="JSON string for adapter config override (publish only)"),
    notes: Optional[str] = typer.Option(None, help="Notes for bulk op"),
):
    """Generic bulk runner.

    Examples:
      python -m ae.cli bulk-run --action validate --db acq.db --geo-city brisbane --page-status draft
      python -m ae.cli bulk-run --action pause --db acq.db --client-id c1 --execute
      python -m ae.cli bulk-run --action publish --db acq.db --template-id trade_lp --execute
    """
    act = action.strip().lower()
    ids = [p.strip() for p in page_ids.split(",")] if page_ids else None

    if act == "validate":
        op = service.run_bulk_validate(
            db,
            page_ids=ids,
            page_status=page_status,
            client_id=client_id,
            template_id=template_id,
            geo_city=geo_city,
            geo_country=geo_country,
            limit=limit,
            mode="dry_run",
            notes=notes,
        )
        typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} action={op.action}")
        typer.echo(json.dumps(op.result_json.get("counters", {}), indent=2))
        return

    if act == "pause":
        mode = "execute" if execute else "dry_run"
        op = service.run_bulk_pause(
            db,
            page_ids=ids,
            page_status=page_status,
            client_id=client_id,
            template_id=template_id,
            geo_city=geo_city,
            geo_country=geo_country,
            limit=limit,
            mode=mode,
            notes=notes,
        )
        typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} mode={op.mode} action={op.action}")
        typer.echo(json.dumps(op.result_json.get("counters", {}), indent=2))
        return

    if act == "publish":
        mode = "execute" if execute else "dry_run"
        override = None
        if adapter_override_json:
            try:
                override = json.loads(adapter_override_json)
            except Exception as e:
                raise typer.BadParameter(f"Invalid JSON for --adapter-override-json: {e}")

        op = service.run_bulk_publish(
            db,
            page_ids=ids,
            page_status=page_status,
            client_id=client_id,
            template_id=template_id,
            geo_city=geo_city,
            geo_country=geo_country,
            limit=limit,
            mode=mode,
            force=force,
            notes=notes,
            adapter_config_override=override,
        )
        typer.echo(f"OK: bulk_id={op.bulk_id} status={op.status} mode={op.mode} action={op.action}")
        typer.echo(json.dumps(op.result_json.get("counters", {}), indent=2))
        return

    raise typer.BadParameter("Unsupported --action. Use: validate|pause|publish")



@app.command()
def serve_console(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Auto-reload (dev)"),
):
    """Run the Operator Console (FastAPI).

    Env:
      AE_CONSOLE_SECRET: if set, requests must send header X-AE-SECRET
    """
    try:
        import uvicorn
    except Exception as e:
        raise typer.BadParameter(f"uvicorn not available: {e}")

    uvicorn.run("ae.console_app:app", host=host, port=port, reload=reload)



@app.command("run-public")
def run_public_api(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8001, help="Port to bind"),
    reload: bool = typer.Option(False, help="Auto-reload (dev)"),
):
    """Run the Public API (FastAPI) for website lead intake.

    Note: this serves only `/lead` and should typically be deployed behind stricter edge controls.
    """
    try:
        import uvicorn
    except Exception as e:
        raise typer.BadParameter(f"uvicorn not available: {e}")

    uvicorn.run("ae.public_api:app", host=host, port=port, reload=reload)


@app.command("work-sync-patches")
def work_sync_patches(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    dry_run: bool = typer.Option(False, help="Print planned changes, do not modify files"),
):
    """Sync PATCH_QUEUE status lines from WORK_QUEUE statuses (best-effort).

    Mapping:
    - doing -> 🟨 in-progress
    - done  -> ✅ done
    - open/planned -> no change (we avoid reopening patches automatically)
    """
    from .workqueue import parse_work_queue
    from .patchqueue import set_patch_status

    rows = parse_work_queue(work_queue_path)

    planned_changes = []
    for r in rows:
        pid = (r.patch_id or "").strip()
        if not pid:
            continue
        st = (r.status or "").strip().lower()
        if st == "doing":
            target = "🟨 in-progress"
        elif st == "done":
            target = "✅ done"
        else:
            continue

        planned_changes.append((pid, target))

    # de-dup: last writer wins (done overrides doing if both exist)
    by_pid = {}
    for pid, target in planned_changes:
        by_pid[pid] = target

    if dry_run:
        typer.echo("=== Planned PATCH_QUEUE status updates ===")
        if not by_pid:
            typer.echo("(none)")
            return
        for pid, target in sorted(by_pid.items()):
            typer.echo(f"{pid} -> {target}")
        return

    changed = 0
    for pid, target in by_pid.items():
        if set_patch_status(patch_queue_path, pid, target):
            changed += 1

    typer.echo(f"work-sync-patches: updated {changed} patch statuses")



@app.command("patch-sync-work")
def patch_sync_work(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    create_missing: bool = typer.Option(False, help="If a patch has no work row, create one (open/doing/done)"),
    fallback_assignee: str = typer.Option("unassigned", help="Assignee for created rows"),
    dry_run: bool = typer.Option(False, help="Print planned changes, do not modify files"),
):
    """Sync WORK_QUEUE statuses from PATCH_QUEUE status lines (reverse direction).

    Mapping:
    - 🟨 in-progress -> doing
    - ✅ done        -> done
    - ⬜ planned     -> no change (do not reopen)

    Precedence: done overrides doing if both exist.
    """
    from .patchqueue import parse_patch_queue
    from .workqueue import parse_work_queue, append_work_queue, make_work_item, update_work_for_patch

    patches = parse_patch_queue(patch_queue_path)
    work = parse_work_queue(work_queue_path)
    work_by_patch = {w.patch_id: w for w in work}

    planned = []
    for p in patches:
        st = (p.status or "").strip()
        if st.startswith("✅"):
            planned.append((p.patch_id, "done", p.client_id, p.title))
        elif st.startswith("🟨"):
            planned.append((p.patch_id, "doing", p.client_id, p.title))

    # de-dup: done wins
    by_pid = {}
    for pid, status, client_id, title in planned:
        prev = by_pid.get(pid)
        if prev is None or status == "done":
            by_pid[pid] = (status, client_id, title)

    if dry_run:
        typer.echo("=== Planned WORK_QUEUE updates ===")
        if not by_pid:
            typer.echo("(none)")
            return
        for pid, (status, client_id, title) in sorted(by_pid.items()):
            action = "update"
            if pid not in work_by_patch and create_missing:
                action = "create"
            typer.echo(f"{action}: {pid} -> {status} (client_id={client_id}) {title}")
        return

    changed = 0
    created = 0

    for pid, (status, client_id, title) in by_pid.items():
        if pid in work_by_patch:
            changed += update_work_for_patch(work_queue_path, pid, status=status)
            continue

        if create_missing:
            item = make_work_item(
                patch_id=pid,
                client_id=client_id or "",
                title=title,
                assignee=fallback_assignee,
                status=("open"),
            )
            append_work_queue(work_queue_path, item)
            created += 1
            changed += update_work_for_patch(work_queue_path, pid, status=status)

    typer.echo(f"patch-sync-work: updated {changed} rows; created {created} rows")



@app.command("reconcile-queues")
def reconcile_queues(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    create_missing_work: bool = typer.Option(False, help="Create missing work rows from PATCH_QUEUE done/doing"),
    fallback_assignee: str = typer.Option("unassigned", help="Assignee for created rows"),
    precedence: str = typer.Option("highest", help="Conflict winner for report: work | patch | highest"),
    report_path: str = typer.Option("", help="If set, write reconcile report markdown to this path"),
    apply: bool = typer.Option(False, help="Apply winners back into queues (calls reconcile-apply)"),
    dry_run: bool = typer.Option(False, help="Print planned changes, do not modify files"),
):
    """Bidirectional reconciliation (safe default):

    1) WORK_QUEUE -> PATCH_QUEUE (doing/done updates)
    2) PATCH_QUEUE -> WORK_QUEUE (doing/done updates)

    Default avoids creating new rows; enable create_missing_work to backfill.
    """
    from typer.testing import CliRunner

    runner = CliRunner()

    args1 = [
        "work-sync-patches",
        "--work-queue-path", work_queue_path,
        "--patch-queue-path", patch_queue_path,
    ]
    args2 = [
        "patch-sync-work",
        "--work-queue-path", work_queue_path,
        "--patch-queue-path", patch_queue_path,
        "--fallback-assignee", fallback_assignee,
    ]

    if create_missing_work:
        args2 += ["--create-missing"]
    if dry_run:
        args1 += ["--dry-run"]
        args2 += ["--dry-run"]

    r1 = runner.invoke(app, args1)
    if r1.exit_code != 0:
        typer.echo(r1.output)
        raise typer.Exit(code=1)

    r2 = runner.invoke(app, args2)
    if r2.exit_code != 0:
        typer.echo(r2.output)
        raise typer.Exit(code=1)


    if report_path:
        # Generate report after reconciliation steps (best-effort)
        from typer.testing import CliRunner
        runner2 = CliRunner()
        rr = runner2.invoke(app, [
            "reconcile-report",
            "--work-queue-path", work_queue_path,
            "--patch-queue-path", patch_queue_path,
            "--precedence", precedence,
            "--out-path", report_path,
        ])
        if rr.exit_code != 0:
            typer.echo(rr.output)
            raise typer.Exit(code=1)

    if apply:
        runner3 = CliRunner()
        aa = [
            "reconcile-apply",
            "--work-queue-path", work_queue_path,
            "--patch-queue-path", patch_queue_path,
            "--precedence", precedence,
        ]
        if dry_run:
            aa += ["--dry-run"]
        ra = runner3.invoke(app, aa)
        if ra.exit_code != 0:
            typer.echo(ra.output)
            raise typer.Exit(code=1)

    typer.echo("reconcile-queues: ok")





def _norm_work_status(s: str) -> str:
    v = (s or "").strip().lower()
    if v in ("done",):
        return "done"
    if v in ("doing",):
        return "doing"
    return "planned"


def _norm_patch_status(s: str) -> str:
    v = (s or "").strip()
    if v.startswith("✅"):
        return "done"
    if v.startswith("🟨"):
        return "doing"
    return "planned"


def _rank(state: str) -> int:
    return {"planned": 0, "doing": 1, "done": 2}.get(state, 0)


def _winner(work_state: str, patch_state: str, precedence: str) -> str:
    # precedence: work | patch | highest
    if precedence == "work":
        return work_state
    if precedence == "patch":
        return patch_state
    # highest = monotonic max
    return work_state if _rank(work_state) >= _rank(patch_state) else patch_state


@app.command("reconcile-report")
def reconcile_report(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    precedence: str = typer.Option("highest", help="Conflict winner: work | patch | highest"),
    out_path: str = typer.Option("", help="Write report to this path (markdown). If empty, print only."),
):
    """Generate a conflict report between WORK_QUEUE and PATCH_QUEUE statuses.

    Reports cases where the normalized states differ:
      WORK: open->planned, doing->doing, done->done
      PATCH: ⬜->planned, 🟨->doing, ✅->done

    Winner is chosen by precedence:
      - work: trust WORK_QUEUE
      - patch: trust PATCH_QUEUE
      - highest: choose the higher-progress state (done > doing > planned)
    """
    from .workqueue import parse_work_queue
    from .patchqueue import parse_patch_queue

    work = parse_work_queue(work_queue_path)
    patches = parse_patch_queue(patch_queue_path)

    work_by_patch = {}
    for w in work:
        pid = (w.patch_id or "").strip()
        if not pid:
            continue
        # If multiple rows share a patch_id, choose the highest-progress state for reporting
        st = _norm_work_status(w.status)
        prev = work_by_patch.get(pid)
        if prev is None or _rank(st) > _rank(prev["state"]):
            work_by_patch[pid] = {
                "state": st,
                "status_raw": (w.status or "").strip(),
                "work_id": w.work_id,
                "assignee": w.assignee or "",
                "title": w.title or "",
            }

    patch_by_id = {}
    for p in patches:
        pid = (p.patch_id or "").strip()
        if not pid:
            continue
        st = _norm_patch_status(p.status)
        prev = patch_by_id.get(pid)
        if prev is None or _rank(st) > _rank(prev["state"]):
            patch_by_id[pid] = {
                "state": st,
                "status_raw": (p.status or "").strip(),
                "client_id": p.client_id or "",
                "title": p.title or "",
            }

    all_pids = sorted(set(work_by_patch.keys()) | set(patch_by_id.keys()))

    rows = []
    for pid in all_pids:
        w = work_by_patch.get(pid)
        p = patch_by_id.get(pid)
        ws = w["state"] if w else "planned"
        ps = p["state"] if p else "planned"
        if ws == ps:
            continue
        win = _winner(ws, ps, precedence)
        rows.append({
            "patch_id": pid,
            "work": ws,
            "patch": ps,
            "winner": win,
            "work_id": (w["work_id"] if w else ""),
            "assignee": (w["assignee"] if w else ""),
            "client_id": (p["client_id"] if p else ""),
            "title": (p["title"] if p and p["title"] else (w["title"] if w else "")),
        })

    header = "# Reconcile Report\n\n"
    meta = f"- precedence: `{precedence}`\n- conflicts: `{len(rows)}`\n\n"
    table = "| patch_id | work_state | patch_state | winner | work_id | assignee | client_id | title |\n|---|---|---|---|---|---|---|---|\n"
    body = ""
    for r in rows:
        body += f"| {r['patch_id']} | {r['work']} | {r['patch']} | {r['winner']} | {r['work_id']} | {r['assignee']} | {r['client_id']} | {r['title']} |\n"

    report = header + meta + table + (body if body else "| (none) |  |  |  |  |  |  |  |\n")

    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
        typer.echo(f"reconcile-report: wrote {out_path}")
    else:
        typer.echo(report)



def _state_to_patch_status_line(state: str) -> str:
    if state == "done":
        return "✅ done"
    if state == "doing":
        return "🟨 in-progress"
    return "⬜ planned"


@app.command("reconcile-apply")
def reconcile_apply(
    work_queue_path: str = typer.Option("ops/WORK_QUEUE.md", help="WORK_QUEUE.md path"),
    patch_queue_path: str = typer.Option("ops/PATCH_QUEUE.md", help="PATCH_QUEUE.md path"),
    precedence: str = typer.Option("highest", help="Conflict winner: work | patch | highest"),
    allow_downgrade: bool = typer.Option(False, help="Allow moving state backward (e.g., done -> doing)"),
    dry_run: bool = typer.Option(False, help="Print planned changes, do not modify files"),
):
    """Apply reconciliation winners back into BOTH queues (safe, monotonic by default).

    By default, we only *promote* state forward (planned->doing->done). If precedence
    would cause a downgrade, it is skipped unless --allow-downgrade is set.
    """
    from .workqueue import parse_work_queue, update_work_for_patch
    from .patchqueue import parse_patch_queue, set_patch_status

    work = parse_work_queue(work_queue_path)
    patches = parse_patch_queue(patch_queue_path)

    # Aggregate work state per patch_id (highest wins)
    work_state = {}
    for w in work:
        pid = (w.patch_id or "").strip()
        if not pid:
            continue
        st = _norm_work_status(w.status)
        prev = work_state.get(pid, "planned")
        if _rank(st) > _rank(prev):
            work_state[pid] = st

    # Aggregate patch state per patch_id (highest wins)
    patch_state = {}
    for p in patches:
        pid = (p.patch_id or "").strip()
        if not pid:
            continue
        st = _norm_patch_status(p.status)
        prev = patch_state.get(pid, "planned")
        if _rank(st) > _rank(prev):
            patch_state[pid] = st

    all_pids = sorted(set(work_state.keys()) | set(patch_state.keys()))

    plan = []
    skipped = []
    for pid in all_pids:
        ws = work_state.get(pid, "planned")
        ps = patch_state.get(pid, "planned")
        if ws == ps:
            continue
        win = _winner(ws, ps, precedence)

        # monotonic guard
        if not allow_downgrade:
            if _rank(win) < _rank(ws) or _rank(win) < _rank(ps):
                skipped.append((pid, ws, ps, win))
                continue

        plan.append((pid, ws, ps, win))

    if dry_run:
        typer.echo("=== Planned reconcile-apply changes ===")
        typer.echo(f"precedence: {precedence}  allow_downgrade: {allow_downgrade}")
        typer.echo(f"apply: {len(plan)}  skipped: {len(skipped)}")
        for pid, ws, ps, win in plan:
            typer.echo(f"apply {pid}: work {ws} / patch {ps} -> {win}")
        for pid, ws, ps, win in skipped:
            typer.echo(f"skip {pid}: work {ws} / patch {ps} -> {win} (downgrade blocked)")
        return

    work_updates = 0
    patch_updates = 0

    for pid, ws, ps, win in plan:
        # Apply to PATCH_QUEUE
        target_patch = _state_to_patch_status_line(win)
        if set_patch_status(patch_queue_path, pid, target_patch):
            patch_updates += 1

        # Apply to WORK_QUEUE (only for doing/done; don't auto-reopen)
        if win in ("doing", "done"):
            work_updates += update_work_for_patch(work_queue_path, pid, status=win)

    typer.echo(f"reconcile-apply: patch_updates={patch_updates} work_updates={work_updates} skipped={len(skipped)}")


@app.command("backup-db")
def backup_db_cmd(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    backup_dir: str = typer.Option("ops/backups", help="Directory for backups"),
    label: str = typer.Option("", help="Optional label suffix for backup filename"),
    keep_last: int = typer.Option(30, help="Retain N most recent backups"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="Log horizon file path"),
):
    """Create a deterministic db backup with checksum + manifest."""
    from .ops_health import backup_db as _backup
    from .workqueue import append_log_horizon

    res = _backup(db_path=db, backup_dir=backup_dir, label=label, keep_last=keep_last)
    meta = res.get("backup", {})
    pruned = res.get("pruned", [])
    msg = (
        f"**DB backup**\n"
        f"- db: `{db}`\n"
        f"- backup: `{meta.get('db_backup')}`\n"
        f"- sha256: `{meta.get('sha256')}`\n"
        f"- bytes: `{meta.get('bytes')}`\n"
        f"- pruned: {len(pruned)}\n"
    )
    append_log_horizon(log_path, msg)
    typer.echo(json.dumps(res, indent=2))


@app.command("restore-db")
def restore_db_cmd(
    db: str = typer.Option(..., help="Path to sqlite db file (destination)"),
    backup_path: str = typer.Option(..., help="Backup .db file to restore from"),
    verify_checksum: bool = typer.Option(True, help="Verify checksum if manifest exists"),
    prebackup: bool = typer.Option(True, help="Create a pre-restore backup if destination exists"),
    backup_dir: str = typer.Option("ops/backups", help="Directory for backups (for prebackup)"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="Log horizon file path"),
):
    """Restore db from a backup file. Writes an audit entry into LOG_HORIZON."""
    from .ops_health import restore_db as _restore
    from .workqueue import append_log_horizon

    res = _restore(db_path=db, backup_path=backup_path, verify_checksum=verify_checksum, prebackup=prebackup, backup_dir=backup_dir)
    msg = (
        f"**DB restore**\n"
        f"- restored_to: `{res.get('restored_to')}`\n"
        f"- from_backup: `{res.get('from_backup')}`\n"
        f"- prebackup: `{(res.get('prebackup') or {}).get('db_backup') if res.get('prebackup') else None}`\n"
        f"- bytes: `{res.get('bytes')}`\n"
    )
    append_log_horizon(log_path, msg)
    typer.echo(json.dumps(res, indent=2))


@app.command("ops-health")
def ops_health_cmd(
    db: str = typer.Option(..., help="Path to sqlite db file"),
    backup_dir: str = typer.Option("ops/backups", help="Directory for backups"),
    log: bool = typer.Option(False, help="If set, append health snapshot to LOG_HORIZON"),
    log_path: str = typer.Option("ops/LOG_HORIZON.md", help="Log horizon file path"),
):
    """Show minimal ops health: db readability, disk, last backup, last publish."""
    from .ops_health import ops_health as _health
    from .workqueue import append_log_horizon

    res = _health(db_path=db, backup_dir=backup_dir)
    if log:
        checks = res.get("checks", {})
        msg = (
            f"**Ops health** `{res.get('status')}`\n"
            f"- db: `{checks.get('db_path')}` exists={checks.get('db_exists')} readable={checks.get('db_readable', None)}\n"
            f"- last_publish_utc: `{checks.get('last_publish_utc')}`\n"
            f"- last_event_utc: `{checks.get('last_event_utc')}`\n"
            f"- latest_backup: `{checks.get('latest_backup')}`\n"
            f"- backup_count: `{checks.get('backup_count')}`\n"
            f"- disk_free_pct: `{(checks.get('disk') or {}).get('free_pct')}`\n"
        )
        append_log_horizon(log_path, msg)
    typer.echo(json.dumps(res, indent=2))


def main():
    app()



@app.command("auth-create-user")
def auth_create_user(
    username: str = typer.Option(..., help="Username (stored lowercase)"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    role: str = typer.Option("admin", help="admin|operator|viewer"),
    db: str = typer.Option("", help="DB path override (otherwise AE_DB_PATH)"),
):
    """Create a console user."""
    db_path = db.strip() or os.getenv("AE_DB_PATH", "").strip() or "data/acq.db"
    uid = create_user(db_path, username=username, password=password, role=role)
    typer.echo(f"auth-create-user: ok user_id={uid} username={username.strip().lower()} role={role}")


@app.command("auth-set-password")
def auth_set_password(
    username: str = typer.Option(..., help="Username"),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    db: str = typer.Option("", help="DB path override (otherwise AE_DB_PATH)"),
):
    """Rotate a user's password."""
    db_path = db.strip() or os.getenv("AE_DB_PATH", "").strip() or "data/acq.db"
    n = set_password(db_path, username=username, password=password)
    if n == 0:
        raise typer.Exit(code=1)
    typer.echo(f"auth-set-password: ok username={username.strip().lower()}")


@app.command("auth-create-api-key")
def auth_create_api_key(
    tenant_id: str = typer.Option(..., help="Tenant ID (client_id when shared DB)"),
    name: str = typer.Option("default", help="Key name for identification"),
    db: str = typer.Option("", help="Auth DB path override (otherwise AE_DB_PATH)"),
):
    """Create a tenant-scoped API key for public endpoints.
    Use X-AE-API-KEY header or Authorization: Bearer <key>.
    The raw key is shown once only."""
    from .api_keys import create_api_key

    db_path = db.strip() or os.getenv("AE_DB_PATH", "").strip() or "data/acq.db"
    raw = create_api_key(db_path, tenant_id=tenant_id, name=name)
    typer.echo("API key created. Store securely - shown once only:")
    typer.echo(raw)


@app.command("onboarding-init")
def onboarding_init(
    db: str = typer.Option(..., help="DB path"),
    client_id: str = typer.Option(..., help="Client ID"),
    overwrite: bool = typer.Option(False, help="Overwrite existing templates"),
):
    """Seed onboarding templates for a client (UTM policy, naming, event map)."""
    dbmod.init_db(db)
    if overwrite:
        for k, v in repo.DEFAULT_ONBOARDING_TEMPLATES.items():
            repo.upsert_onboarding_template(db, client_id, k, v)
        typer.echo(f"ok: overwritten templates for {client_id}")
        raise typer.Exit(0)

    items = repo.ensure_default_onboarding_templates(db, client_id)
    typer.echo(f"ok: ensured {len(items)} templates for {client_id}")

if __name__ == "__main__":
    main()