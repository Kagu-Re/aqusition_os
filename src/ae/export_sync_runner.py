from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .export_presets import get_preset as get_registry_preset
from .repo_export_presets import get_export_preset
from .repo_export_jobs import list_export_jobs, get_export_job, update_export_job_run_state
from .export_engine import run_export
from .export_file_writer import write_export_file
from .export_sync_jobs import compute_next_run
from .event_bus import EventBus


def _emit(db_path: str, *, topic: str, correlation_id: str, payload: Dict[str, Any]) -> None:
    # never break the job runner due to telemetry failures
    try:
        EventBus.emit_topic(
            db_path,
            topic=topic,
            correlation_id=correlation_id,
            aggregate_type="job",
            aggregate_id=correlation_id,
            payload=payload,
        )
    except Exception:
        return


def run_due_export_jobs(
    db_path: str,
    *,
    now: Optional[datetime] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Run enabled export jobs whose next_run <= now (or next_run is null).

    v1 target: writes files locally via the preset's output_dir.
    """
    now = now or datetime.now(timezone.utc)
    # EventBus is static in this codebase

    jobs = list_export_jobs(db_path, limit=500)
    due = []
    for j in jobs:
        if not j.get("enabled"):
            continue
        nr = j.get("next_run")
        if nr is None:
            due.append(j)
        else:
            try:
                nr_dt = datetime.fromisoformat(nr)
            except Exception:
                due.append(j)
                continue
            if nr_dt <= now:
                due.append(j)
    due = sorted(due, key=lambda x: (x.get("next_run") or ""))[:limit]

    results: List[Dict[str, Any]] = []
    for meta in due:
        job_id = meta["job_id"]
        job = get_export_job(db_path, job_id)
        if not job:
            continue

        correlation_id = f"job:{job.job_id}"
        _emit(db_path, topic="op.crm.sync.started", correlation_id=correlation_id, payload={"job_id": job.job_id, "preset_name": job.preset_name})

        try:
            p_db = get_export_preset(db_path, job.preset_name)
            pz = p_db or get_registry_preset(job.preset_name)
            if not pz:
                raise ValueError(f"Unknown export preset: {job.preset_name}")

            rows = run_export(db_path, pz.schema_name, limit=100000, client_id=None)
            ts = now.strftime("%Y%m%d-%H%M%S")
            filename = f"{job.preset_name}-{ts}-{job.job_id[:8]}"
            out_path, row_count = write_export_file(job.output_dir or "generated/exports", filename, pz, rows)

            next_run = compute_next_run(job.cron, now=now).isoformat()
            update_export_job_run_state(db_path, job.job_id, last_run=now.isoformat(), next_run=next_run, fail_count=0, last_error=None)

            _emit(db_path, topic="op.crm.export.file_generated", correlation_id=correlation_id, payload={"preset_name": job.preset_name, "output_path": out_path, "row_count": row_count})
            _emit(db_path, topic="op.crm.sync.completed", correlation_id=correlation_id, payload={"job_id": job.job_id, "preset_name": job.preset_name, "output_path": out_path, "row_count": row_count})

            results.append({"job_id": job.job_id, "preset_name": job.preset_name, "status": "ok", "output_path": out_path, "row_count": row_count, "next_run": next_run})
        except Exception as e:
            fail_count = int(job.fail_count or 0) + 1
            next_run = compute_next_run(job.cron, now=now).isoformat()
            update_export_job_run_state(db_path, job.job_id, last_run=now.isoformat(), next_run=next_run, fail_count=fail_count, last_error=str(e))
            _emit(db_path, topic="op.crm.sync.failed", correlation_id=correlation_id, payload={"job_id": job.job_id, "preset_name": job.preset_name, "error": str(e), "fail_count": fail_count})
            results.append({"job_id": job.job_id, "preset_name": job.preset_name, "status": "error", "error": str(e), "fail_count": fail_count, "next_run": next_run})

    return {"now": now.isoformat(), "count": len(results), "results": results}
