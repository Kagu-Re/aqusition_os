from __future__ import annotations

# Import bulk package operations
from .service_bulk_packages import run_bulk_update_packages, run_bulk_delete_packages

from typing import Dict, List, Tuple
import uuid

from .models import PublishLog, ChangeLog, WorkItem, EventRecord, AdStat
from .enums import PageStatus, PublishAction, LogResult, WorkStatus, WorkType, Priority, EventName
from . import repo
from .event_bus import EventBus
from .adapters.registry import resolve_adapters
from .policies import publish_readiness


def _hash_file(path: str) -> str:
    import hashlib
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _publisher_out_dir_key(publisher_name: str) -> str:
    # maps adapter to its output dir config key
    if publisher_name == "tailwind_static":
        return "static_out_dir"
    if publisher_name == "local_file":
        return "publish_out_dir"
    if publisher_name == "framer_stub":
        return "framer_out_dir"
    if publisher_name == "webflow_stub":
        return "webflow_out_dir"
    # fallback (best effort)
    return "publish_out_dir"


def preview_page(
    db_path: str,
    page_id: str,
    *,
    preview_dir: str,
    adapter_config_override: dict | None = None,
) -> tuple[bool, list[str], str | None, dict]:
    """Render a publish artifact into a preview directory WITHOUT mutating page status.

    Returns: (ok, errors, preview_artifact_path, meta)
    meta includes: publisher, target_artifact_path, preview_hash, target_hash, changed
    """
    from pathlib import Path
    ok, errors = validate_page(db_path, page_id)
    page = repo.get_page(db_path, page_id)
    if not page:
        return False, [f"Page not found: {page_id}"], None, {}

    if not ok:
        return False, errors, None, {}

    # resolve adapters w/ preview override
    base = adapter_config_override or {}
    adapters0 = resolve_adapters(repo, base)
    key = _publisher_out_dir_key(adapters0.config.publisher)
    preview_override = dict(base)
    preview_override[key] = preview_dir
    adapters = resolve_adapters(repo, preview_override)

    client = repo.get_client(db_path, page.client_id)
    payload = adapters.content.build(page_id, context={"page": page, "client": client})
    pub_res = adapters.publisher.publish(page_id, payload, context={"page": page, "client": client, "db_path": db_path})

    if not pub_res.ok:
        return False, (pub_res.errors or ["preview_publish_failed"]), None, {}

    # compute target artifact path best-effort
    publisher = adapters0.config.publisher
    target_dir = getattr(adapters0.config, _publisher_out_dir_key(publisher))
    if publisher == "tailwind_static":
        target_path = str(Path(target_dir) / page_id / "index.html")
    elif publisher == "local_file":
        target_path = str(Path(target_dir) / f"{page_id}.json")
    else:
        target_path = pub_res.artifact_path or ""

    preview_path = pub_res.artifact_path or ""
    ph = _hash_file(preview_path) if preview_path else ""
    th = _hash_file(target_path) if target_path else ""
    meta = {
        "publisher": publisher,
        "preview_dir": preview_dir,
        "target_dir": target_dir,
        "preview_artifact_path": preview_path,
        "target_artifact_path": target_path,
        "preview_hash": ph,
        "target_hash": th,
        "changed": (ph != th) if (ph and th) else True,  # if no target -> treat as changed
    }
    return True, [], preview_path, meta

def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

def validate_page(db_path: str, page_id: str) -> Tuple[bool, List[str]]:
    page = repo.get_page(db_path, page_id)
    if not page:
        return False, [f"Page not found: {page_id}"]
    client = repo.get_client(db_path, page.client_id)
    if not client:
        return False, [f"Client not found: {page.client_id}"]
    template = repo.get_template(db_path, page.template_id)
    if not template:
        return False, [f"Template not found: {page.template_id}"]

    has_events = repo.has_validated_events(db_path, page_id)
    ok, errors = publish_readiness(client, page, template, has_events=has_events)
    return ok, errors

def publish_page(db_path: str, page_id: str, notes: str | None = None, adapter_config_override: dict | None = None) -> tuple[bool, list[str]]:
    ok, errors = validate_page(db_path, page_id)
    page = repo.get_page(db_path, page_id)
    if not page:
        return False, [f"Page not found: {page_id}"]

    if not ok:
        log = PublishLog(
            log_id=_id("pub"),
            client_id=page.client_id,
            page_id=page.page_id,
            template_id=page.template_id,
            template_version=page.template_version,
            content_version=page.content_version,
            action=PublishAction.publish,
            result=LogResult.fail,
            notes="; ".join(errors) if not notes else f"{notes} | {'; '.join(errors)}",
        )
        repo.insert_publish_log(db_path, log)
        return False, errors

    # Adapter boundary: build payload + publish (local stubs by default)
    adapters = resolve_adapters(repo, adapter_config_override)
    client = repo.get_client(db_path, page.client_id)
    payload = adapters.content.build(page_id, context={"page": page, "client": client})
    pub_res = adapters.publisher.publish(page_id, payload, context={"page": page, "client": client, "db_path": db_path})
    if not pub_res.ok:
        log = PublishLog(
            log_id=_id("pub"),
            client_id=page.client_id,
            page_id=page.page_id,
            template_id=page.template_id,
            template_version=page.template_version,
            content_version=page.content_version,
            action=PublishAction.publish,
            result=LogResult.fail,
            notes="; ".join(pub_res.errors or []) if not notes else f"{notes} | {'; '.join(pub_res.errors or [])}",
        )
        repo.insert_publish_log(db_path, log)
        return False, (pub_res.errors or ["publish_failed"])

    repo.update_page_status(db_path, page_id, PageStatus.live)
    if pub_res.artifact_path and not notes:
        notes = f"published_artifact={pub_res.artifact_path}"
    elif pub_res.artifact_path and notes:
        notes = f"{notes} | published_artifact={pub_res.artifact_path}"

    log = PublishLog(
        log_id=_id("pub"),
        client_id=page.client_id,
        page_id=page.page_id,
        template_id=page.template_id,
        template_version=page.template_version,
        content_version=page.content_version,
        action=PublishAction.publish,
        result=LogResult.success,
        notes=notes,
    )
    repo.insert_publish_log(db_path, log)
    return True, []

def pause_page(db_path: str, page_id: str, notes: str | None = None) -> None:
    page = repo.get_page(db_path, page_id)
    if not page:
        raise ValueError(f"Page not found: {page_id}")
    repo.update_page_status(db_path, page_id, PageStatus.paused)
    log = PublishLog(
        log_id=_id("pub"),
        client_id=page.client_id,
        page_id=page.page_id,
        template_id=page.template_id,
        template_version=page.template_version,
        content_version=page.content_version,
        action=PublishAction.pause,
        result=LogResult.success,
        notes=notes,
    )
    repo.insert_publish_log(db_path, log)

def log_change(db_path: str, page_id: str, changed_fields: List[str], notes: str | None = None) -> ChangeLog:
    page = repo.get_page(db_path, page_id)
    if not page:
        raise ValueError(f"Page not found: {page_id}")
    before, after = repo.bump_content_version(db_path, page_id)
    log = ChangeLog(
        log_id=_id("chg"),
        client_id=page.client_id,
        page_id=page_id,
        content_version_before=before,
        content_version_after=after,
        changed_fields=changed_fields,
        notes=notes,
    )
    repo.insert_change_log(db_path, log)
    return log

def enqueue_work(
    db_path: str,
    type_value: WorkType,
    client_id: str,
    page_id: str | None,
    priority_value: Priority,
    acceptance: str | None,
) -> WorkItem:
    item = WorkItem(
        work_item_id=_id("wk"),
        type=type_value,
        client_id=client_id,
        page_id=page_id,
        priority=priority_value,
        acceptance_criteria=acceptance,
        status=WorkStatus.new,
    )
    repo.upsert_work_item(db_path, item)
    return item

def record_event(db_path: str, page_id: str, event_name: EventName, params: Dict[str, object] | None = None) -> EventRecord:
    ev = EventRecord(
        event_id=_id("ev"),
        page_id=page_id,
        event_name=event_name,
        params_json=params or {},
    )
    repo.insert_event(db_path, ev)
    return ev


def run_bulk_op(db_path: str, bulk_id: str) -> dict:
    op = repo.get_bulk_op(db_path, bulk_id)
    if not op:
        raise ValueError(f"Bulk op not found: {bulk_id}")

    result = {"bulk_id": bulk_id, "action": op.action, "mode": op.mode, "items": []}
    repo.update_bulk_op(db_path, bulk_id, "running", result)

    page_ids = op.selector_json.get("page_ids", [])
    if not page_ids:
        result["error"] = "selector_json.page_ids is required for v0.1.1"
        repo.update_bulk_op(db_path, bulk_id, "failed", result)
        return result

    try:
        for pid in page_ids:
            if op.action == "validate":
                ok, errors = validate_page(db_path, pid)
                result["items"].append({"page_id": pid, "ok": ok, "errors": errors})
            elif op.action == "publish":
                if op.mode == "dry_run":
                    ok, errors = validate_page(db_path, pid)
                    result["items"].append({"page_id": pid, "would_publish": ok, "errors": errors})
                else:
                    ok, errors = publish_page(db_path, pid, notes=op.notes)
                    result["items"].append({"page_id": pid, "published": ok, "errors": errors})
            elif op.action == "pause":
                if op.mode == "dry_run":
                    result["items"].append({"page_id": pid, "would_pause": True})
                else:
                    pause_page(db_path, pid, notes=op.notes)
                    result["items"].append({"page_id": pid, "paused": True})
            else:
                raise ValueError(f"Unsupported bulk action: {op.action}")

        repo.update_bulk_op(db_path, bulk_id, "done", result)
        return result
    except Exception as e:
        result["error"] = str(e)
        repo.update_bulk_op(db_path, bulk_id, "failed", result)
        return result


def run_bulk_publish(
    db_path: str,
    page_ids: List[str] | None = None,
    page_status: str | None = None,
    client_id: str | None = None,
    template_id: str | None = None,
    geo_city: str | None = None,
    geo_country: str | None = None,
    limit: int = 200,
    mode: str = "dry_run",
    force: bool = False,
    notes: str | None = None,
    adapter_config_override: dict | None = None,
) -> BulkOp:
    """Bulk publish runner (P-20260201-0007).

    Q-0003 additions:
    - Preview render into `exports/previews/<bulk_id>/`
    - Diff counters: changed vs unchanged
    - Validate gate before execute publish (unless force=True)
    """
    from .models import BulkOp  # local import to avoid widening top imports
    import uuid
    from datetime import datetime
    from pathlib import Path

    bulk_id = f"bulk_{uuid.uuid4().hex[:12]}"
    selector: dict = {}
    if page_ids:
        selector["page_ids"] = page_ids
    if page_status:
        selector["page_status"] = page_status
    if client_id:
        selector["client_id"] = client_id
    if template_id:
        selector["template_id"] = template_id
    if geo_city:
        selector["geo_city"] = geo_city
    if geo_country:
        selector["geo_country"] = geo_country
    selector["limit"] = limit

    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action="publish",
        selector_json=selector,
        status="queued",
        result_json={
            "pages": [],
            "counters": {
                "total": 0,
                "published": 0,
                "skipped": 0,
                "failed": 0,
                "previewed": 0,
                "changed": 0,
                "unchanged": 0,
            },
        },
        notes=notes,
    )
    repo.insert_bulk_op(db_path, op)

    # claim lock
    if not repo.try_claim_bulk_op(db_path, bulk_id):
        repo.update_bulk_op(db_path, bulk_id, "failed", {"error": "bulk_op_not_claimed"})
        op.status = "failed"
        try:
            repo.append_activity(
                db_path,
                action="bulk_publish",
                entity_type="bulk_op",
                entity_id=str(op.bulk_id),
                actor="system",
                details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
            )
        except Exception:
            pass
        return op

    # resolve targets
    targets: List[str] = _resolve_bulk_targets(db_path, selector, default_status=PageStatus.draft)

    # validate gate before execute publish (unless force=True)
    if mode != "dry_run" and not force:
        invalid: list[dict] = []
        for pid in targets:
            ok, errs = validate_page(db_path, pid)
            if not ok:
                invalid.append({"page_id": pid, "errors": errs})
        if invalid:
            result = op.result_json
            result["counters"]["total"] = len(targets)
            result["counters"]["failed"] = len(invalid)
            result["validation_gate"] = {"ok": False, "failed": invalid}
            repo.update_bulk_op(db_path, bulk_id, "failed", result)
            op.status = "failed"
            op.result_json = result
            op.updated_at = datetime.utcnow()
            try:
                repo.append_activity(
                    db_path,
                    action="bulk_publish_gate_failed",
                    entity_type="bulk_op",
                    entity_id=str(op.bulk_id),
                    actor="system",
                    details={"failed_count": len(invalid)},
                )
            except Exception:
                pass
            return op

    # preview directory for this bulk op
    preview_root = Path("exports/previews") / bulk_id
    preview_root.mkdir(parents=True, exist_ok=True)

    result = op.result_json
    result["counters"]["total"] = len(targets)
    result["preview_dir"] = str(preview_root)
    repo.update_bulk_op(db_path, bulk_id, "running", result)

    for pid in targets:
        page = repo.get_page(db_path, pid)
        if not page:
            entry = {"page_id": pid, "status": "failed", "reason": "page_not_found"}
            result["pages"].append(entry)
            result["counters"]["failed"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        # legacy idempotency: already live skip (execute), unless force
        if (page.page_status == PageStatus.live) and (not force) and (mode != "dry_run"):
            entry = {"page_id": pid, "status": "skipped", "reason": "already_live"}
            result["pages"].append(entry)
            result["counters"]["skipped"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        # dry-run: validate + preview + diff
        if mode == "dry_run":
            ok, errs = validate_page(db_path, pid)
            if not ok:
                entry = {"page_id": pid, "status": "failed", "errors": errs}
                result["counters"]["failed"] += 1
                result["pages"].append(entry)
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue

            ok2, errs2, _, meta = preview_page(
                db_path,
                pid,
                preview_dir=str(preview_root),
                adapter_config_override=adapter_config_override,
            )
            if ok2:
                entry = {"page_id": pid, "status": "would_publish", "preview": meta}
                result["counters"]["previewed"] += 1
                if meta.get("changed"):
                    result["counters"]["changed"] += 1
                else:
                    result["counters"]["unchanged"] += 1
            else:
                entry = {"page_id": pid, "status": "failed", "errors": errs2}
                result["counters"]["failed"] += 1

            result["pages"].append(entry)
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        # execute: preview + diff (best-effort) then publish
        ok2, errs2, _, meta = preview_page(
            db_path,
            pid,
            preview_dir=str(preview_root),
            adapter_config_override=adapter_config_override,
        )
        if ok2:
            result["counters"]["previewed"] += 1
            if meta.get("changed"):
                result["counters"]["changed"] += 1
            else:
                result["counters"]["unchanged"] += 1

        # skip if unchanged and already live unless force (extra idempotency)
        if ok2 and (not meta.get("changed")) and (page.page_status == PageStatus.live) and (not force):
            entry = {"page_id": pid, "status": "skipped", "reason": "unchanged_live", "preview": meta}
            result["pages"].append(entry)
            result["counters"]["skipped"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        ok, errs = publish_page(db_path, pid, notes=notes, adapter_config_override=adapter_config_override)
        if ok:
            entry = {"page_id": pid, "status": "published", "preview": meta if ok2 else None}
            result["counters"]["published"] += 1
        else:
            entry = {"page_id": pid, "status": "failed", "errors": errs, "preview": meta if ok2 else None}
            result["counters"]["failed"] += 1

        result["pages"].append(entry)
        repo.update_bulk_op(db_path, bulk_id, "running", result)

    # finalize
    final_status = "done"
    repo.update_bulk_op(db_path, bulk_id, final_status, result)
    op.status = final_status
    op.result_json = result
    op.updated_at = datetime.utcnow()

    # activity log (append-only)
    try:
        repo.append_activity(
            db_path,
            action="bulk_publish",
            entity_type="bulk_op",
            entity_id=str(op.bulk_id),
            actor="system",
            details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
        )
    except Exception:
        pass

    return op



def kpi_report(
    db_path: str,
    page_id: str,
    impressions: int | None = None,
    clicks: int | None = None,
    spend: float | None = None,
    revenue: float | None = None,
    since_iso: str | None = None,
    platform: str | None = None,
    adapter_config_override: dict | None = None,
) -> Dict[str, Any]:
    adapters = resolve_adapters(repo, adapter_config_override)
    ctx: Dict[str, Any] = {"db_path": db_path}
    if impressions is not None:
        ctx["impressions"] = impressions
    if clicks is not None:
        ctx["clicks"] = clicks
    if spend is not None:
        ctx["spend"] = spend
    if revenue is not None:
        ctx["revenue"] = revenue
    if since_iso is not None:
        ctx["since_iso"] = since_iso
    if platform is not None:
        ctx["platform"] = platform
    return adapters.analytics.kpis(page_id, ctx)

def export_kpis(
    db_path: str,
    out_path: str,
    fmt: str = "json",
    page_ids: List[str] | None = None,
    page_status: str | None = None,
    limit: int = 200,
    impressions: int | None = None,
    clicks: int | None = None,
    spend: float | None = None,
    revenue: float | None = None,
    since_iso: str | None = None,
    platform: str | None = None,
    adapter_config_override: dict | None = None,
) -> str:
    """Export KPI report for many pages into JSON or CSV."""
    if page_ids is None:
        st = page_status or PageStatus.draft
        pages = repo.list_pages(db_path, status=st, limit=limit)
        page_ids = [p.page_id for p in pages]

    rows: List[Dict[str, Any]] = []
    for pid in page_ids:
        rep = kpi_report(
            db_path,
            pid,
            impressions=impressions,
            clicks=clicks,
            spend=spend,
            revenue=revenue,
            since_iso=since_iso,
            platform=platform,
            adapter_config_override=adapter_config_override,
        )
        k = rep["kpis"]
        rows.append({
            "page_id": pid,
            "impressions": k.get("impressions"),
            "clicks": k.get("clicks"),
            "spend": k.get("spend"),
            "revenue": k.get("revenue"),
            "leads": k.get("leads"),
            "bookings": k.get("bookings"),
            "ctr": k.get("ctr"),
            "lead_rate": k.get("lead_rate"),
            "booking_rate": k.get("booking_rate"),
            "lead_to_booking_rate": k.get("lead_to_booking_rate"),
            "cpc": k.get("cpc"),
            "cpl": k.get("cpl"),
            "cpa": k.get("cpa"),
            "aov": k.get("aov"),
            "roas": k.get("roas"),
        })

    import os, json, csv
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if fmt == "json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"pages": rows}, f, indent=2)
    elif fmt == "csv":
        cols = list(rows[0].keys()) if rows else ["page_id"]
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            wtr = csv.DictWriter(f, fieldnames=cols)
            wtr.writeheader()
            for row in rows:
                wtr.writerow(row)
    else:
        raise ValueError(f"Unknown fmt: {fmt}")

    return out_path


def record_ad_stat(
    db_path: str,
    page_id: str,
    platform: str,
    impressions: int | None = None,
    clicks: int | None = None,
    spend: float | None = None,
    revenue: float | None = None,
    campaign_id: str | None = None,
    adset_id: str | None = None,
    ad_id: str | None = None,
    timestamp_iso: str | None = None,
) -> str:
    import uuid
    from datetime import datetime
    ts = datetime.utcnow() if timestamp_iso is None else datetime.fromisoformat(timestamp_iso)
    stat_id = f"ad_{uuid.uuid4().hex[:12]}"
    stat = AdStat(
        stat_id=stat_id,
        timestamp=ts,
        page_id=page_id,
        platform=platform,
        campaign_id=campaign_id,
        adset_id=adset_id,
        ad_id=ad_id,
        impressions=impressions,
        clicks=clicks,
        spend=spend,
        revenue=revenue,
    )
    repo.insert_ad_stat(db_path, stat)
    return stat_id


def import_ad_stats_csv(
    db_path: str,
    csv_path: str,
    default_platform: str | None = None,
    default_page_id: str | None = None,
    timestamp_col: str = "timestamp",
    dry_run: bool = False,
) -> dict:
    """Import ad stats from a normalized CSV into ad_stats.

    Expected columns (case-insensitive):
      - page_id (optional if default_page_id provided)
      - platform (optional if default_platform provided)
      - timestamp (optional; if missing uses now)
      - impressions, clicks, spend, revenue (optional)
      - campaign_id, adset_id, ad_id (optional)

    Any additional columns are ignored.

    Returns counters: inserted, skipped, failed.
    """
    import csv as _csv
    from datetime import datetime
    counters = {"rows": 0, "inserted": 0, "skipped": 0, "failed": 0}
    errors: list[dict] = []

    def _lower_map(row: dict) -> dict:
        return {(k or "").strip().lower(): v for k, v in row.items()}

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f)
        for raw in reader:
            counters["rows"] += 1
            row = _lower_map(raw)

            page_id = (row.get("page_id") or default_page_id or "").strip()
            platform = (row.get("platform") or default_platform or "").strip().lower()

            if not page_id or not platform:
                counters["failed"] += 1
                errors.append({"row": counters["rows"], "error": "missing page_id/platform"})
                continue

            ts = (row.get(timestamp_col) or row.get("timestamp") or "").strip()
            if ts:
                try:
                    ts_norm = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
                    dt = datetime.fromisoformat(ts_norm)
                except Exception:
                    dt = datetime.utcnow()
            else:
                dt = datetime.utcnow()

            def _int(x):
                x = (x or "").strip()
                if x == "":
                    return None
                return int(float(x))

            def _float(x):
                x = (x or "").strip()
                if x == "":
                    return None
                return float(x)

            impressions = _int(row.get("impressions"))
            clicks = _int(row.get("clicks"))
            spend = _float(row.get("spend"))
            revenue = _float(row.get("revenue"))

            campaign_id = (row.get("campaign_id") or "").strip() or None
            adset_id = (row.get("adset_id") or "").strip() or None
            ad_id = (row.get("ad_id") or "").strip() or None

            if dry_run:
                counters["skipped"] += 1
                continue

            try:
                record_ad_stat(
                    db_path,
                    page_id,
                    platform=platform,
                    impressions=impressions,
                    clicks=clicks,
                    spend=spend,
                    revenue=revenue,
                    campaign_id=campaign_id,
                    adset_id=adset_id,
                    ad_id=ad_id,
                    timestamp_iso=dt.isoformat(),
                )
                counters["inserted"] += 1
            except Exception as e:
                counters["failed"] += 1
                errors.append({"row": counters["rows"], "error": str(e)})

    return {"counters": counters, "errors": errors}


def _normalize_row_for_ad_stats(row: dict, mapping: dict, defaults: dict) -> dict:
    """Map a vendor row -> normalized ad_stats row.
    mapping: normalized_key -> list of possible source keys (lowercased)
    defaults: values to apply if missing.
    """
    low = {(k or "").strip().lower(): v for k, v in row.items()}
    out = {}
    for nk, candidates in mapping.items():
        val = None
        for ck in candidates:
            if ck in low and str(low.get(ck)).strip() != "":
                val = low.get(ck)
                break
        if val is None and nk in defaults:
            val = defaults[nk]
        out[nk] = val
    return out

def import_meta_export_csv(
    db_path: str,
    csv_path: str,
    default_page_id: str,
    default_platform: str = "meta",
    aliases_path: str = "ops/ad_platform_aliases.json",
    dry_run: bool = False,
) -> dict:
    """Import Meta Ads Manager export CSV into ad_stats."""
    import csv as _csv
    from datetime import datetime

    aliases = load_ad_platform_aliases(aliases_path).get("meta", {})

    mapping = {
        "timestamp": aliases.get("timestamp", ["date start","date_start","day","date","date stop","date_stop"]),
        "impressions": aliases.get("impressions", ["impressions"]),
        "clicks": aliases.get("clicks", ["clicks","link clicks","link_clicks","unique link clicks","unique_link_clicks"]),
        "spend": aliases.get("spend", ["amount spent (usd)","amount spent","spend","cost"]),
        "revenue": aliases.get("revenue", ["purchase conversion value","website purchases conversion value","omni purchase conversion value","purchase value","conversion value"]),
        "campaign_id": aliases.get("campaign_id", ["campaign id","campaign_id"]),
        "adset_id": aliases.get("adset_id", ["ad set id","adset id","adset_id"]),
        "ad_id": aliases.get("ad_id", ["ad id","ad_id"]),
    }
    defaults = {"page_id": default_page_id, "platform": default_platform}

    counters = {"rows": 0, "inserted": 0, "skipped": 0, "failed": 0}
    errors: list[dict] = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f)
        for raw in reader:
            counters["rows"] += 1
            norm = _normalize_row_for_ad_stats(raw, mapping, defaults)

            ts = (norm.get("timestamp") or "").strip()
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    dt = datetime.utcnow()
            else:
                dt = datetime.utcnow()

            def _int(x):
                x = (x or "").strip()
                if x == "":
                    return None
                return int(float(x.replace(",", "")))

            def _float(x):
                x = (x or "").strip()
                if x == "":
                    return None
                return float(x.replace(",", ""))

            try:
                if dry_run:
                    counters["skipped"] += 1
                    continue

                record_ad_stat(
                    db_path,
                    default_page_id,
                    platform=default_platform,
                    impressions=_int(norm.get("impressions")),
                    clicks=_int(norm.get("clicks")),
                    spend=_float(norm.get("spend")),
                    revenue=_float(norm.get("revenue")),
                    campaign_id=(norm.get("campaign_id") or "").strip() or None,
                    adset_id=(norm.get("adset_id") or "").strip() or None,
                    ad_id=(norm.get("ad_id") or "").strip() or None,
                    timestamp_iso=dt.isoformat(),
                )
                counters["inserted"] += 1
            except Exception as e:
                counters["failed"] += 1
                errors.append({"row": counters["rows"], "error": str(e)})

    return {"counters": counters, "errors": errors}

def import_google_ads_export_csv(
    db_path: str,
    csv_path: str,
    default_page_id: str,
    default_platform: str = "google",
    aliases_path: str = "ops/ad_platform_aliases.json",
    dry_run: bool = False,
) -> dict:
    """Import Google Ads export CSV into ad_stats."""
    import csv as _csv
    from datetime import datetime

    aliases = load_ad_platform_aliases(aliases_path).get("google", {})

    mapping = {
        "timestamp": aliases.get("timestamp", ["day","date"]),
        "impressions": aliases.get("impressions", ["impressions"]),
        "clicks": aliases.get("clicks", ["clicks"]),
        "spend": aliases.get("spend", ["cost","cost (aud)","cost (usd)","cost (thb)"]),
        "revenue": aliases.get("revenue", ["conversion value","conv. value","all conv. value","total conv. value"]),
        "campaign_id": aliases.get("campaign_id", ["campaign id","campaign_id"]),
        "adset_id": aliases.get("adset_id", ["ad group id","ad group","adgroup id","adgroup_id"]),
        "ad_id": aliases.get("ad_id", ["ad id","ad_id"]),
    }
    counters = {"rows": 0, "inserted": 0, "skipped": 0, "failed": 0}
    errors: list[dict] = []

    def _pick(low: dict, keys: list[str]):
        for k in keys:
            if k in low and str(low.get(k)).strip() != "":
                return low.get(k)
        return None

    def _int(x):
        x = (x or "").strip()
        if x == "":
            return None
        return int(float(x.replace(",", "")))

    def _float(x):
        x = (x or "").strip()
        if x == "":
            return None
        return float(x.replace(",", ""))

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = _csv.DictReader(f)
        for raw in reader:
            counters["rows"] += 1
            low = {(k or "").strip().lower(): v for k, v in raw.items()}

            ts = (_pick(low, mapping["timestamp"]) or "").strip()
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception:
                    dt = datetime.utcnow()
            else:
                dt = datetime.utcnow()

            try:
                if dry_run:
                    counters["skipped"] += 1
                    continue

                record_ad_stat(
                    db_path,
                    default_page_id,
                    platform=default_platform,
                    impressions=_int(_pick(low, mapping["impressions"])),
                    clicks=_int(_pick(low, mapping["clicks"])),
                    spend=_float(_pick(low, mapping["spend"])),
                    revenue=_float(_pick(low, mapping["revenue"])),
                    campaign_id=(_pick(low, mapping["campaign_id"]) or "").strip() or None,
                    adset_id=(_pick(low, mapping["adset_id"]) or "").strip() or None,
                    ad_id=(_pick(low, mapping["ad_id"]) or "").strip() or None,
                    timestamp_iso=dt.isoformat(),
                )
                counters["inserted"] += 1
            except Exception as e:
                counters["failed"] += 1
                errors.append({"row": counters["rows"], "error": str(e)})

    return {"counters": counters, "errors": errors}


def load_ad_platform_aliases(path: str = "ops/ad_platform_aliases.json") -> dict:
    """Load alias registry for platform CSV header mapping.

    This keeps mappers out of code: extend by editing JSON (append new headers).
    """
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def validate_ad_platform_aliases(path: str = "ops/ad_platform_aliases.json") -> dict:
    """Validate alias registry structure and return a coverage summary.

    Checks:
    - JSON parse ok
    - each platform is an object
    - each metric is list[str] with non-empty entries
    - no duplicates within metric lists (case-insensitive)
    """
    aliases = load_ad_platform_aliases(path)
    issues: list[dict] = []
    coverage: dict = {}

    if not isinstance(aliases, dict):
        return {"ok": False, "issues": [{"error": "aliases_root_not_object"}], "coverage": {}, "path": path}

    for platform, metrics in aliases.items():
        if not isinstance(metrics, dict):
            issues.append({"platform": platform, "error": "platform_metrics_not_object"})
            continue
        coverage[platform] = {}
        for metric, vals in metrics.items():
            if not isinstance(vals, list):
                issues.append({"platform": platform, "metric": metric, "error": "metric_aliases_not_list"})
                continue
            seen = set()
            dups = []
            empties = 0
            valid = 0
            for v in vals:
                sv = ("" if v is None else str(v)).strip()
                if sv == "":
                    empties += 1
                    continue
                key = sv.lower()
                if key in seen:
                    dups.append(sv)
                else:
                    seen.add(key)
                    valid += 1
            if empties:
                issues.append({"platform": platform, "metric": metric, "error": "empty_aliases", "count": empties})
            if dups:
                issues.append({"platform": platform, "metric": metric, "error": "duplicate_aliases", "values": dups})
            if valid == 0:
                issues.append({"platform": platform, "metric": metric, "error": "no_valid_aliases"})
            coverage[platform][metric] = {"count": valid}

    return {"ok": len(issues) == 0, "issues": issues, "coverage": coverage, "path": path}


def _resolve_bulk_targets(
    db_path: str,
    selector: dict,
    default_status: str | None = None,
) -> list[str]:
    """Resolve selector_json to a list of page_ids.

    Supported keys:
    - page_ids: explicit list
    - page_status
    - client_id
    - template_id
    - geo_city
    - geo_country
    - limit
    """
    if selector.get("page_ids"):
        return list(selector["page_ids"])

    page_status = selector.get("page_status") or default_status
    client_id = selector.get("client_id")
    template_id = selector.get("template_id")
    geo_city = selector.get("geo_city")
    geo_country = selector.get("geo_country")
    limit = int(selector.get("limit") or 200)

    pages = repo.list_pages_filtered(
        db_path,
        page_status=page_status,
        client_id=client_id,
        template_id=template_id,
        geo_city=geo_city,
        geo_country=geo_country,
        limit=limit,
    )
    return [p.page_id for p in pages]



def _clamp(s: str | None, n: int) -> str | None:
    if s is None:
        return None
    s = str(s)
    if len(s) <= n:
        return s
    return s[:n]

def _sanitize_utm(utm: dict | None) -> dict:
    """Allow only known UTM keys + cap value lengths."""
    if not utm or not isinstance(utm, dict):
        return {}
    allow = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}
    out = {}
    for k in list(utm.keys()):
        if k in allow:
            v = utm.get(k)
            if v is None:
                continue
            out[k] = _clamp(str(v), 128)
    return out

def score_lead_spam(*, name: str | None, phone: str | None, email: str | None, message: str | None) -> tuple[int, list[str]]:
    import re
    """Very small, explainable heuristics. No ML. No PII storage required beyond form fields."""
    score = 0
    reasons: list[str] = []

    msg = (message or "").strip()
    nm = (name or "").strip()
    em = (email or "").strip().lower()
    ph = (phone or "").strip()

    if not msg:
        score += 30
        reasons.append("empty_message")
    if len(msg) > 2000:
        score += 20
        reasons.append("very_long_message")
    if any(x in msg.lower() for x in ["viagra", "casino", "crypto", "loan", "forex", "seo backlinks"]):
        score += 40
        reasons.append("spam_keywords")
    if em and any(em.endswith(d) for d in [".ru", ".cn"]) and ("chiang" in msg.lower() or "thailand" in msg.lower()):
        # weak signal; keep low
        score += 10
        reasons.append("suspicious_tld")
    if nm and len(nm) == 1:
        score += 10
        reasons.append("tiny_name")
    if ph and len(re.sub(r"\D+", "", ph)) < 7:
        score += 15
        reasons.append("short_phone")

    return score, reasons


def _notify_lead(*, lead_id: int, payload: dict) -> None:
    """Notification adapter placeholder.
    For now: writes to activity_log and prints to stdout (works in server logs).
    Later: email/SMS/Line/WhatsApp adapters.
    """
    try:
        # keep minimal and safe
        print(f"[lead_notify] lead_id={lead_id} client_id={payload.get('client_id')} page_id={payload.get('page_id')}")
    except Exception:
        pass


def intake_lead(
    db_path: str,
    *,
    source: str | None,
    page_id: str | None,
    client_id: str | None,
    name: str | None,
    phone: str | None,
    email: str | None,
    message: str | None,
    utm: dict | None,
    referrer: str | None,
    user_agent: str | None,
    ip_hint: str | None,
) -> tuple[int, dict]:
    """Stores lead, emits activity, and triggers notification (best-effort)."""
    from datetime import datetime
    import json as _json
    from .models import LeadIntake

    name = _clamp(name, 80)
    phone = _clamp(phone, 32)
    email = _clamp(email, 254)
    message = _clamp(message, 2000)
    referrer = _clamp(referrer, 512)
    user_agent = _clamp(user_agent, 512)
    utm = _sanitize_utm(utm)

    spam_score, spam_reasons = score_lead_spam(name=name, phone=phone, email=email, message=message)
    is_spam = 1 if spam_score >= 60 else 0

    ts = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    lead = LeadIntake(
        ts=ts,
        source=source,
        page_id=page_id,
        client_id=client_id,
        name=name,
        phone=phone,
        email=email,
        message=message,
        utm_source=(utm or {}).get("utm_source"),
        utm_medium=(utm or {}).get("utm_medium"),
        utm_campaign=(utm or {}).get("utm_campaign"),
        utm_term=(utm or {}).get("utm_term"),
        utm_content=(utm or {}).get("utm_content"),
        referrer=referrer,
        user_agent=user_agent,
        ip_hint=ip_hint,
        spam_score=int(spam_score),
        is_spam=int(is_spam),
        status="new" if not is_spam else "spam",
        meta_json={"spam_reasons": spam_reasons, "utm_keys": list((utm or {}).keys())},
    )
    lead_id = repo.insert_lead(db_path, lead)

    # activity log
    try:
        repo.append_activity(
            db_path,
            action="lead_intake",
            entity_type="lead",
            entity_id=str(lead_id),
            actor="external",
            details={"client_id": client_id, "page_id": page_id, "is_spam": bool(is_spam), "spam_score": spam_score},
        )
    except Exception:
        pass

    # notify only non-spam by default
    if not is_spam:
        try:
            _notify_lead(lead_id=lead_id, payload={"client_id": client_id, "page_id": page_id})
        except Exception:
            pass

    return lead_id, {"is_spam": bool(is_spam), "spam_score": spam_score, "spam_reasons": spam_reasons}


def set_lead_outcome(
    db_path: str,
    lead_id: int,
    *,
    status: str | None = None,
    booking_status: str | None = None,
    booking_value: float | None = None,
    booking_currency: str | None = None,
    booking_ts: str | None = None,
    actor: str = "operator",
) -> None:
    """Minimal outcome capture: lead -> booking -> value.

    OP-BOOK-002A: booking lifecycle emission.
    If booking_status transitions to a known state, emit an operational booking event.
    """
    prev_booking_status: str | None = None
    try:
        prev = repo.get_lead(db_path, int(lead_id))
        prev_booking_status = getattr(prev, "booking_status", None) if prev else None
    except Exception:
        prev_booking_status = None

    repo.update_lead_outcome(
        db_path,
        int(lead_id),
        status=status,
        booking_status=booking_status,
        booking_value=booking_value,
        booking_currency=booking_currency,
        booking_ts=booking_ts,
    )

    # Emit booking events when booking_status changes.
    try:
        if booking_status is not None and booking_status != prev_booking_status:
            topic = None
            bs = str(booking_status).strip().lower()
            if bs == "booked":
                topic = "op.booking.created"
            elif bs == "confirmed":
                topic = "op.booking.confirmed"
            elif bs in {"cancelled", "canceled"}:
                topic = "op.booking.cancelled"
            elif bs == "completed":
                topic = "op.booking.completed"

            if topic:
                booking_id = f"lead-{int(lead_id)}"
                EventBus.emit_topic(
                    db_path,
                    topic=topic,
                    aggregate_type="booking",
                    aggregate_id=booking_id,
                    payload={
                        "booking_id": booking_id,
                        "lead_id": int(lead_id),
                        "booking_status": booking_status,
                        "booking_value": booking_value,
                        "booking_currency": booking_currency,
                        "booking_ts": booking_ts,
                    },
                    actor=actor,
                    correlation_id=f"lead:{int(lead_id)}",
                    causation_id=None,
                )
    except Exception:
        # v1 best-effort: do not break outcome capture.
        pass

    try:
        repo.append_activity(
            db_path,
            action="lead_outcome_update",
            entity_type="lead",
            entity_id=str(lead_id),
            actor=actor,
            details={
                "status": status,
                "booking_status": booking_status,
                "booking_value": booking_value,
                "booking_currency": booking_currency,
                "booking_ts": booking_ts,
            },
        )
    except Exception:
        pass

def run_bulk_validate(
    db_path: str,
    page_ids: List[str] | None = None,
    page_status: str | None = None,
    client_id: str | None = None,
    template_id: str | None = None,
    geo_city: str | None = None,
    geo_country: str | None = None,
    limit: int = 200,
    mode: str = "dry_run",
    notes: str | None = None,
) -> BulkOp:
    """Bulk validate runner.

    mode is kept for symmetry (dry_run|execute) but validation is the same.
    """
    from .models import BulkOp
    import uuid

    bulk_id = f"bulk_{uuid.uuid4().hex[:12]}"
    selector = {
        "limit": limit,
    }
    if page_ids:
        selector["page_ids"] = page_ids
    if page_status:
        selector["page_status"] = page_status
    if client_id:
        selector["client_id"] = client_id
    if template_id:
        selector["template_id"] = template_id
    if geo_city:
        selector["geo_city"] = geo_city
    if geo_country:
        selector["geo_country"] = geo_country
    if client_id:
        selector["client_id"] = client_id
    if template_id:
        selector["template_id"] = template_id
    if geo_city:
        selector["geo_city"] = geo_city
    if geo_country:
        selector["geo_country"] = geo_country

    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action="validate",
        selector_json=selector,
        status="queued",
        result_json={"pages": [], "counters": {"total": 0, "ok": 0, "failed": 0}},
        notes=notes,
    )
    repo.insert_bulk_op(db_path, op)

    if not repo.try_claim_bulk_op(db_path, bulk_id):
        repo.update_bulk_op(db_path, bulk_id, "failed", {"error": "bulk_op_not_claimed"})
        op.status = "failed"
        # activity log (append-only)
        try:
            repo.append_activity(
                db_path,
                action="bulk_validate",
                entity_type="bulk_op",
                entity_id=str(op.bulk_id),
                actor="system",
                details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
            )
        except Exception:
            pass
        return op

    targets = _resolve_bulk_targets(db_path, selector, default_status=None)
    result = op.result_json
    result["counters"]["total"] = len(targets)
    repo.update_bulk_op(db_path, bulk_id, "running", result)

    for pid in targets:
        ok, errors = validate_page(db_path, pid)
        entry = {"page_id": pid, "ok": ok, "errors": errors}
        result["pages"].append(entry)
        if ok:
            result["counters"]["ok"] += 1
        else:
            result["counters"]["failed"] += 1
        repo.update_bulk_op(db_path, bulk_id, "running", result)

    repo.update_bulk_op(db_path, bulk_id, "done", result)
    op.status = "done"
    op.result_json = result
    # activity log (append-only)
    try:
        repo.append_activity(
            db_path,
            action="bulk_validate",
            entity_type="bulk_op",
            entity_id=str(op.bulk_id),
            actor="system",
            details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
        )
    except Exception:
        pass
    return op


def run_bulk_pause(
    db_path: str,
    page_ids: List[str] | None = None,
    page_status: str | None = None,
    client_id: str | None = None,
    template_id: str | None = None,
    geo_city: str | None = None,
    geo_country: str | None = None,
    limit: int = 200,
    mode: str = "dry_run",
    notes: str | None = None,
) -> BulkOp:
    """Bulk pause runner.

    - dry_run: reports would_pause (skips missing pages)
    - execute: pauses pages not already paused
    """
    from .models import BulkOp
    import uuid

    bulk_id = f"bulk_{uuid.uuid4().hex[:12]}"
    selector = {"limit": limit}
    if page_ids:
        selector["page_ids"] = page_ids
    if page_status:
        selector["page_status"] = page_status
    if client_id:
        selector["client_id"] = client_id
    if template_id:
        selector["template_id"] = template_id
    if geo_city:
        selector["geo_city"] = geo_city
    if geo_country:
        selector["geo_country"] = geo_country
    if client_id:
        selector["client_id"] = client_id
    if template_id:
        selector["template_id"] = template_id
    if geo_city:
        selector["geo_city"] = geo_city
    if geo_country:
        selector["geo_country"] = geo_country

    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action="pause",
        selector_json=selector,
        status="queued",
        result_json={"pages": [], "counters": {"total": 0, "paused": 0, "skipped": 0, "failed": 0}},
        notes=notes,
    )
    repo.insert_bulk_op(db_path, op)

    if not repo.try_claim_bulk_op(db_path, bulk_id):
        repo.update_bulk_op(db_path, bulk_id, "failed", {"error": "bulk_op_not_claimed"})
        op.status = "failed"
        # activity log (append-only)
        try:
            repo.append_activity(
                db_path,
                action="bulk_pause",
                entity_type="bulk_op",
                entity_id=str(op.bulk_id),
                actor="system",
                details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
            )
        except Exception:
            pass
        return op

    targets = _resolve_bulk_targets(db_path, selector, default_status=None)
    result = op.result_json
    result["counters"]["total"] = len(targets)
    repo.update_bulk_op(db_path, bulk_id, "running", result)

    for pid in targets:
        page = repo.get_page(db_path, pid)
        if not page:
            result["pages"].append({"page_id": pid, "status": "failed", "reason": "page_not_found"})
            result["counters"]["failed"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        if page.page_status == PageStatus.paused:
            result["pages"].append({"page_id": pid, "status": "skipped", "reason": "already_paused"})
            result["counters"]["skipped"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        if mode == "dry_run":
            result["pages"].append({"page_id": pid, "status": "would_pause"})
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            continue

        pause_page(db_path, pid, notes=notes)
        result["pages"].append({"page_id": pid, "status": "paused"})
        result["counters"]["paused"] += 1
        repo.update_bulk_op(db_path, bulk_id, "running", result)

    repo.update_bulk_op(db_path, bulk_id, "done", result)
    op.status = "done"
    op.result_json = result
    # activity log (append-only)
    try:
        repo.append_activity(
            db_path,
            action="bulk_pause",
            entity_type="bulk_op",
            entity_id=str(op.bulk_id),
            actor="system",
            details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
        )
    except Exception:
        pass
    return op
