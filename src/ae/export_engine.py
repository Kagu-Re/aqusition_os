from __future__ import annotations

"""Export engine.

OP-CRM-001A: resolves a schema (DB override -> registry) and produces JSON rows.

v1 focuses on operational reporting for operators; CSV/XLSX presets are in OP-CRM-001B.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from . import repo
from .models import ExportSchema
from .export_registry import get_schema as get_registry_schema
from .repo_export_schemas import get_export_schema as get_db_schema
from .event_bus import EventBus


def resolve_schema(db_path: str, name: str) -> ExportSchema:
    s = get_db_schema(db_path, name)
    if s is not None:
        return s
    return get_registry_schema(name)


def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def run_export(
    db_path: str,
    schema_name: str,
    *,
    limit: int = 200,
    client_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    schema = resolve_schema(db_path, schema_name)

    # hydrate entities
    leads = []
    payments = []
    if any(f.entity == "lead" for f in schema.fields):
        leads = repo.list_leads(db_path, limit=limit, client_id=client_id)
        # schema-specific filter
        if schema_name == "bookings_basic":
            leads = [l for l in leads if (getattr(l, "booking_status", None) not in (None, "", "none"))]
    if any(f.entity == "payment" for f in schema.fields):
        payments = repo.list_payments(db_path, limit=limit)

    # build rows
    rows: List[Dict[str, Any]] = []
    if schema_name == "payments_basic":
        for p in payments:
            row: Dict[str, Any] = {}
            for f in schema.fields:
                v = _get_path(p, f.path)
                if v is None:
                    v = f.default
                if f.required and v is None:
                    v = f.default
                row[f.out_key] = v
            rows.append(row)
    else:
        for l in leads:
            row = {}
            for f in schema.fields:
                if f.entity != "lead":
                    continue
                v = _get_path(l, f.path)
                if v is None:
                    v = f.default
                row[f.out_key] = v
            rows.append(row)

    # emit operational event (best-effort)
    try:
        EventBus.emit_topic(
            db_path=db_path,
            topic="op.crm.exported",
            aggregate_type="export",
            aggregate_id=schema_name,
            payload={
                "schema_name": schema_name,
                "schema_version": int(schema.schema_version),
                "row_count": len(rows),
                "client_id": client_id,
                "ts": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            },
            actor="system",
        )
    except Exception:
        pass

    return rows
