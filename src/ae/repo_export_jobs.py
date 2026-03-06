from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import connect
from .models import ExportJob


def upsert_export_job(db_path: str, job: ExportJob) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO export_jobs(job_id, preset_name, cron, target, output_dir, enabled, last_run, next_run, fail_count, last_error, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET
                preset_name=excluded.preset_name,
                cron=excluded.cron,
                target=excluded.target,
                output_dir=excluded.output_dir,
                enabled=excluded.enabled,
                last_run=excluded.last_run,
                next_run=excluded.next_run,
                fail_count=excluded.fail_count,
                last_error=excluded.last_error,
                updated_at=excluded.updated_at
            """,
            (
                job.job_id,
                job.preset_name,
                job.cron,
                job.target,
                job.output_dir,
                1 if job.enabled else 0,
                job.last_run,
                job.next_run,
                int(job.fail_count),
                job.last_error,
                now,
            ),
        )
        conn.commit()


def create_export_job(
    db_path: str,
    preset_name: str,
    cron: str,
    target: str = "local",
    output_dir: str = "generated/exports",
    enabled: bool = True,
    next_run: Optional[str] = None,
) -> ExportJob:
    job = ExportJob(
        job_id=uuid.uuid4().hex,
        preset_name=preset_name,
        cron=cron,
        target=target,
        output_dir=output_dir,
        enabled=enabled,
        last_run=None,
        next_run=next_run,
        fail_count=0,
        last_error=None,
    )
    upsert_export_job(db_path, job)
    return job


def get_export_job(db_path: str, job_id: str) -> Optional[ExportJob]:
    with connect(db_path) as conn:
        row = conn.execute(
            """SELECT job_id, preset_name, cron, target, output_dir, enabled, last_run, next_run, fail_count, last_error
               FROM export_jobs WHERE job_id=?""",
            (job_id,),
        ).fetchone()
    if not row:
        return None
    return ExportJob(
        job_id=row[0],
        preset_name=row[1],
        cron=row[2],
        target=row[3],
        output_dir=row[4] or "generated/exports",
        enabled=bool(row[5]),
        last_run=row[6],
        next_run=row[7],
        fail_count=int(row[8] or 0),
        last_error=row[9],
    )


def list_export_jobs(db_path: str, limit: int = 200) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            """SELECT job_id, preset_name, cron, target, output_dir, enabled, last_run, next_run, fail_count, last_error, updated_at
               FROM export_jobs ORDER BY updated_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            "job_id": r[0],
            "preset_name": r[1],
            "cron": r[2],
            "target": r[3],
            "output_dir": r[4],
            "enabled": bool(r[5]),
            "last_run": r[6],
            "next_run": r[7],
            "fail_count": int(r[8] or 0),
            "last_error": r[9],
            "updated_at": r[10],
        }
        for r in rows
    ]


def update_export_job_run_state(
    db_path: str,
    job_id: str,
    *,
    last_run: Optional[str] = None,
    next_run: Optional[str] = None,
    fail_count: Optional[int] = None,
    last_error: Optional[str] = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE export_jobs
            SET last_run=COALESCE(?, last_run),
                next_run=COALESCE(?, next_run),
                fail_count=COALESCE(?, fail_count),
                last_error=?,
                updated_at=?
            WHERE job_id=?
            """,
            (last_run, next_run, fail_count, last_error, now, job_id),
        )
        conn.commit()
