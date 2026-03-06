from __future__ import annotations

import os
import tempfile
import gc
from datetime import datetime, timezone

from ae import db as dbmod
from ae.repo_export_jobs import create_export_job
from ae.export_sync_jobs import parse_cron, compute_next_run
from ae.export_sync_runner import run_due_export_jobs
from tests.test_helpers import force_close_db_connections


def test_cron_parse_and_next_run():
    spec = parse_cron("*/5 * * * *")
    assert spec.kind == "interval_minutes"
    now = datetime(2026, 2, 5, 0, 0, 0, tzinfo=timezone.utc)
    nr = compute_next_run("*/5 * * * *", now=now)
    assert nr > now


def test_export_job_runs_and_writes_file():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "t.db")
        out_dir = os.path.join(td, "out")
        try:
            dbmod.init_db(db_path)

            # registry preset exists
            job = create_export_job(
                db_path,
                preset_name="leads_csv_basic",
                cron="*/5 * * * *",
                target="local",
                output_dir=out_dir,
                enabled=True,
                next_run=None,
            )

            res = run_due_export_jobs(db_path, now=datetime.now(timezone.utc), limit=10)
            assert res["count"] == 1
            r0 = res["results"][0]
            assert r0["job_id"] == job.job_id
            assert r0["status"] == "ok"
            assert os.path.exists(r0["output_path"])
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()