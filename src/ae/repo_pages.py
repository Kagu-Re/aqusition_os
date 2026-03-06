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

_page_adapter = TypeAdapter(Page)

def upsert_page(db_path: str, page: Page) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO pages(page_id, client_id, template_id, template_version, page_slug, page_url, page_status,
                                   content_version, service_focus, locale)
                 VALUES(?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(page_id) DO UPDATE SET
                    client_id=excluded.client_id,
                    template_id=excluded.template_id,
                    template_version=excluded.template_version,
                    page_slug=excluded.page_slug,
                    page_url=excluded.page_url,
                    page_status=excluded.page_status,
                    content_version=excluded.content_version,
                    service_focus=excluded.service_focus,
                    locale=excluded.locale
            """,
            (
                page.page_id, page.client_id, page.template_id, page.template_version, page.page_slug, page.page_url,
                page.page_status.value, page.content_version, page.service_focus, page.locale
            )
        )
        con.commit()
    finally:
        con.close()

def get_page(db_path: str, page_id: str) -> Optional[Page]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM pages WHERE page_id=?", (page_id,))
        if not row:
            return None
        d = dict(row)
        d["page_status"] = d["page_status"]
        return _page_adapter.validate_python(d)
    finally:
        con.close()

def update_page_status(db_path: str, page_id: str, status: PageStatus) -> None:
    con = db.connect(db_path)
    try:
        con.execute("UPDATE pages SET page_status=? WHERE page_id=?", (status.value, page_id))
        con.commit()
    finally:
        con.close()

def bump_content_version(db_path: str, page_id: str) -> Tuple[int,int]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT content_version FROM pages WHERE page_id=?", (page_id,))
        if not row:
            raise ValueError("Page not found")
        before = int(row["content_version"])
        after = before + 1
        con.execute("UPDATE pages SET content_version=? WHERE page_id=?", (after, page_id))
        con.commit()
        return before, after
    finally:
        con.close()

def list_pages(db_path: str, status: Optional[str] = None, limit: int = 200) -> List[Page]:
    con = db.connect(db_path)
    try:
        if status:
            rows = db.fetchall(con, "SELECT * FROM pages WHERE page_status=? LIMIT ?", (status, limit))
        else:
            rows = db.fetchall(con, "SELECT * FROM pages LIMIT ?", (limit,))
        return [_page_adapter.validate_python(dict(r)) for r in rows]
    finally:
        con.close()

def list_pages_filtered(
    db_path: str,
    page_status: Optional[str] = None,
    client_id: Optional[str] = None,
    template_id: Optional[str] = None,
    geo_city: Optional[str] = None,
    geo_country: Optional[str] = None,
    limit: int = 200,
) -> List[Page]:
    """List pages using simple selectors used by bulk ops.

    geo_city/geo_country are resolved via join to clients table.
    """
    con = db.connect(db_path)
    try:
        clauses = []
        params: list = []
        join_clients = False

        if page_status:
            clauses.append("p.page_status=?")
            params.append(page_status)
        if client_id:
            clauses.append("p.client_id=?")
            params.append(client_id)
        if template_id:
            clauses.append("p.template_id=?")
            params.append(template_id)
        if geo_city:
            join_clients = True
            clauses.append("c.geo_city=?")
            params.append(geo_city)
        if geo_country:
            join_clients = True
            clauses.append("c.geo_country=?")
            params.append(geo_country)

        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        if join_clients:
            sql = f"""SELECT p.* FROM pages p
JOIN clients c ON p.client_id=c.client_id
{where_sql}
LIMIT ?"""
        else:
            sql = f"""SELECT p.* FROM pages p
{where_sql}
LIMIT ?"""

        params.append(limit)
        rows = db.fetchall(con, sql, tuple(params))
        return [_page_adapter.validate_python(dict(r)) for r in rows]
    finally:
        con.close()

