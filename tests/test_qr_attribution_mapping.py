import os
import tempfile
import gc
from datetime import datetime

from ae import db as dbmod
from ae import repo
from ae.event_bus import EventBus
from ae.repo_op_events import list_op_events
from ae.models import Menu
from ae.enums import MenuStatus
from tests.test_helpers import force_close_db_connections


def test_qr_attribution_mapping_and_scan_log():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "acq.db")
        try:
            dbmod.init_db(db_path)

            repo.upsert_menu(
            db_path,
            Menu(
                menu_id="m1",
                client_id="c1",
                name="menu-1",
                title="Menu 1",
                description=None,
                status=MenuStatus.draft,
                created_at=datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
                updated_at=datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
                meta={"public_url": "https://example.com/menu-m1.html"},
            ),
            )

            base_url = "https://example.com/menu-m1.html"
            attr = repo.create_qr_attribution(
                db_path,
                kind="menu",
                menu_id="m1",
                url=base_url + "?aid=test-aid",
                meta={"base_url": base_url},
                attribution_id="test-aid",
            )
            assert attr.attribution_id == "test-aid"
            assert "aid=test-aid" in attr.url

            # Emit a generated event (should persist)
            EventBus.emit_topic(
                db_path,
                topic="op.qr.generated",
                aggregate_type="qr",
                aggregate_id=attr.attribution_id,
                payload={"attribution_id": attr.attribution_id, "kind": "menu", "url": attr.url, "menu_id": "m1"},
            )

            # Scan logging + scanned event
            repo.insert_qr_scan(db_path, attribution_id=attr.attribution_id, meta={"referrer": "x"})
            EventBus.emit_topic(
                db_path,
                topic="op.qr.scanned",
                aggregate_type="qr",
                aggregate_id=attr.attribution_id,
                payload={"attribution_id": attr.attribution_id, "url": attr.url, "menu_id": "m1", "kind": "menu"},
            )

            scans = repo.list_qr_scans(db_path, attribution_id=attr.attribution_id, limit=10)
            assert len(scans) == 1

            evs = list_op_events(db_path, aggregate_type="qr", aggregate_id=attr.attribution_id, limit=10)
            topics = [e.topic for e in evs]
            assert "op.qr.generated" in topics
            assert "op.qr.scanned" in topics
        finally:
            # Force close connections before cleanup (Windows file locking fix)
            if os.path.exists(db_path):
                force_close_db_connections(db_path)
            gc.collect()
