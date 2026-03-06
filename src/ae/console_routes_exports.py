from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional

from .console_support import require_role
from .export_registry import SCHEMAS as REGISTRY_SCHEMAS, get_schema as get_registry_schema
from .repo_export_schemas import list_export_schemas, get_export_schema
from .export_engine import resolve_schema, run_export
from .export_presets import PRESETS as REGISTRY_PRESETS, get_preset as get_registry_preset
from .repo_export_presets import list_export_presets, get_export_preset, upsert_export_preset
from .export_file_writer import write_export_file
from datetime import datetime, timezone

from .repo_export_jobs import list_export_jobs, create_export_job, get_export_job, upsert_export_job
from .export_sync_jobs import compute_next_run
from .export_sync_runner import run_due_export_jobs


router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/schemas")
def list_schemas(
    db: str,
    _: None = Depends(require_role("viewer")),
):
    overrides = {s["name"]: s for s in list_export_schemas(db, limit=500)}
    items = []
    for name, s in REGISTRY_SCHEMAS.items():
        items.append(
            {
                "name": name,
                "schema_version": int(s.schema_version),
                "source": "db_override" if name in overrides else "registry",
                "override_updated_at": overrides.get(name, {}).get("updated_at"),
                "field_count": len(s.fields),
            }
        )
    # include DB-only schemas (not in registry)
    for name, meta in overrides.items():
        if name not in REGISTRY_SCHEMAS:
            items.append(
                {
                    "name": name,
                    "schema_version": int(meta["schema_version"]),
                    "source": "db_override",
                    "override_updated_at": meta.get("updated_at"),
                    "field_count": None,
                }
            )
    items.sort(key=lambda x: x["name"])
    return {"count": len(items), "items": items}


@router.get("/schemas/{name}")
def get_schema(
    name: str,
    db: str,
    _: None = Depends(require_role("viewer")),
):
    s = resolve_schema(db, name)
    return {"schema": s.model_dump()}


@router.post("/run/{name}")
def run(
    name: str,
    db: str,
    limit: int = 200,
    client_id: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    rows = run_export(db, name, limit=limit, client_id=client_id)
    return {"schema_name": name, "row_count": len(rows), "rows": rows}


@router.get("/presets")
def list_presets(db: str, _: None = Depends(require_role("viewer"))):
    overrides = {p["name"]: p for p in list_export_presets(db, limit=500)}
    items = []
    for name, pz in REGISTRY_PRESETS.items():
        items.append({
            "name": name,
            "preset_version": int(pz.preset_version),
            "schema_name": pz.schema_name,
            "format": pz.format,
            "source": "db_override" if name in overrides else "registry",
            "override_updated_at": overrides.get(name, {}).get("updated_at"),
            "enabled": bool(pz.enabled),
        })
    for name, meta in overrides.items():
        if name not in REGISTRY_PRESETS:
            items.append({**meta, "source": "db_override"})
    items.sort(key=lambda x: x["name"])
    return {"count": len(items), "items": items}


@router.get("/presets/{name}")
def get_preset(name: str, db: str, _: None = Depends(require_role("viewer"))):
    p_db = get_export_preset(db, name)
    pz = p_db or get_registry_preset(name)
    if not pz:
        return {"preset": None}
    return {"preset": pz.model_dump(), "source": "db_override" if p_db else "registry"}


@router.post("/presets/{name}")
def upsert_preset(name: str, preset: dict, db: str, _: None = Depends(require_role("admin"))):
    from .models import ExportPreset
    pz = ExportPreset(**{**preset, "name": name})
    upsert_export_preset(db, pz)
    return {"status": "ok", "name": name}


@router.post("/run-preset/{name}")
def run_preset(
    name: str,
    db: str,
    limit: int = 200,
    client_id: Optional[str] = None,
    output_dir: str = "generated/exports",
    _: None = Depends(require_role("viewer")),
):
    p_db = get_export_preset(db, name)
    pz = p_db or get_registry_preset(name)
    if not pz:
        raise ValueError(f"Unknown export preset: {name}")
    rows = run_export(db, pz.schema_name, limit=limit, client_id=client_id)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{name}-{ts}"
    out_path, row_count = write_export_file(output_dir, filename, pz, rows)
    return {"preset_name": name, "schema_name": pz.schema_name, "row_count": row_count, "output_path": out_path}


# --- Scheduled sync jobs ---


@router.get("/jobs")
def list_jobs(db: str, limit: int = 200, _: None = Depends(require_role("viewer"))):
    items = list_export_jobs(db, limit=limit)
    return {"count": len(items), "items": items}


@router.post("/jobs")
def create_job(payload: dict, db: str, _: None = Depends(require_role("admin"))):
    preset_name = payload.get("preset_name")
    cron = payload.get("cron")
    target = payload.get("target", "local")
    output_dir = payload.get("output_dir", "generated/exports")
    enabled = bool(payload.get("enabled", True))
    if not preset_name or not cron:
        raise ValueError("preset_name and cron are required")
    next_run = compute_next_run(cron).isoformat()
    job = create_export_job(
        db,
        preset_name=preset_name,
        cron=cron,
        target=target,
        output_dir=output_dir,
        enabled=enabled,
        next_run=next_run,
    )
    return {"status": "ok", "job": job.model_dump()}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: str, _: None = Depends(require_role("viewer"))):
    job = get_export_job(db, job_id)
    return {"job": job.model_dump() if job else None}


@router.post("/jobs/{job_id}/run")
def run_job(job_id: str, db: str, _: None = Depends(require_role("operator"))):
    job = get_export_job(db, job_id)
    if not job:
        raise ValueError("job not found")
    now = datetime.now(timezone.utc)
    job.next_run = now.isoformat()
    upsert_export_job(db, job)
    res = run_due_export_jobs(db, now=now, limit=50)
    # Return the matching result if present
    for r in res.get("results", []):
        if r.get("job_id") == job_id:
            return {"status": "ok", "result": r, "now": res.get("now")}
    return {"status": "ok", "result": None, "now": res.get("now")}


@router.post("/jobs/run-due")
def run_due(db: str, limit: int = 50, _: None = Depends(require_role("operator"))):
    return run_due_export_jobs(db, limit=limit)
