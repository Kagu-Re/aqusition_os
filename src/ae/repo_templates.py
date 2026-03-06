from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import TypeAdapter

from . import db
from .models import (
    Client, Template, Page, WorkItem, PublishLog, ChangeLog, EventRecord, BulkOp, AdStat
)
from .enums import PageStatus, WorkStatus, PublishAction, LogResult

def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)

_template_adapter = TypeAdapter(Template)

def upsert_template(db_path: str, template: Template) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO templates(template_id, template_name, template_version, cms_schema_version,
                                       compatible_events_version, status, changelog, preview_url)
                 VALUES(?,?,?,?,?,?,?,?)
                 ON CONFLICT(template_id) DO UPDATE SET
                    template_name=excluded.template_name,
                    template_version=excluded.template_version,
                    cms_schema_version=excluded.cms_schema_version,
                    compatible_events_version=excluded.compatible_events_version,
                    status=excluded.status,
                    changelog=excluded.changelog,
                    preview_url=excluded.preview_url
            """,
            (
                template.template_id, template.template_name, template.template_version,
                template.cms_schema_version, template.compatible_events_version,
                template.status.value, template.changelog, template.preview_url
            )
        )
        con.commit()
    finally:
        con.close()

def get_template(db_path: str, template_id: str) -> Optional[Template]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM templates WHERE template_id=?", (template_id,))
        if not row:
            return None
        d = dict(row)
        return _template_adapter.validate_python(d)
    finally:
        con.close()

