from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from . import db
from .models import QrAttribution, QrScan


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json(obj: Any) -> str:
    return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))


def create_qr_attribution(
    db_path: str,
    *,
    kind: str,
    url: str,
    menu_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    attribution_id: Optional[str] = None,
) -> QrAttribution:
    """Upsert a QR attribution mapping.

    v1: allow updates to url/meta for the same attribution_id.
    """
    attribution_id = attribution_id or str(uuid4())
    created_at = _now_iso()
    meta_json = _json(meta)

    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO qr_attributions(attribution_id, kind, menu_id, url, meta_json, created_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(attribution_id) DO UPDATE SET
                       kind=excluded.kind,
                       menu_id=excluded.menu_id,
                       url=excluded.url,
                       meta_json=excluded.meta_json""",
            (attribution_id, kind, menu_id, url, meta_json, created_at),
        )
        con.commit()
        row = db.fetchone(con, "SELECT * FROM qr_attributions WHERE attribution_id=?", (attribution_id,))
    finally:
        con.close()

    if not row:
        # Should never happen, but keep function total.
        return QrAttribution(
            attribution_id=attribution_id,
            kind=kind,
            menu_id=menu_id,
            url=url,
            meta_json=meta or {},
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")),
        )

    return QrAttribution(
        attribution_id=row["attribution_id"],
        kind=row["kind"],
        menu_id=row["menu_id"],
        url=row["url"],
        meta_json=json.loads(row["meta_json"] or "{}"),
        created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
    )


def get_qr_attribution(db_path: str, attribution_id: str) -> Optional[QrAttribution]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM qr_attributions WHERE attribution_id=?", (attribution_id,))
        if not row:
            return None
        return QrAttribution(
            attribution_id=row["attribution_id"],
            kind=row["kind"],
            menu_id=row["menu_id"],
            url=row["url"],
            meta_json=json.loads(row["meta_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
        )
    finally:
        con.close()


def list_qr_attributions(
    db_path: str,
    *,
    menu_id: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 50,
) -> List[QrAttribution]:
    sql = "SELECT a.* FROM qr_attributions a"
    params: List[Any] = []
    if client_id:
        sql += " INNER JOIN menus m ON a.menu_id = m.menu_id WHERE m.client_id = ?"
        params.append(client_id)
    if menu_id:
        sql += " AND a.menu_id = ?" if params else " WHERE a.menu_id = ?"
        params.append(menu_id)
    sql += " ORDER BY a.created_at DESC LIMIT ?"
    params.append(limit)

    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[QrAttribution] = []
        for r in rows:
            out.append(QrAttribution(
                attribution_id=r["attribution_id"],
                kind=r["kind"],
                menu_id=r["menu_id"],
                url=r["url"],
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")),
            ))
        return out
    finally:
        con.close()


def insert_qr_scan(
    db_path: str,
    *,
    attribution_id: str,
    meta: Optional[Dict[str, Any]] = None,
    ts_iso: Optional[str] = None,
    scan_id: Optional[str] = None,
) -> QrScan:
    scan_id = scan_id or str(uuid4())
    ts_iso = ts_iso or _now_iso()
    meta_json = _json(meta)

    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO qr_scans(scan_id, attribution_id, ts, meta_json)
                   VALUES(?,?,?,?)""",
            (scan_id, attribution_id, ts_iso, meta_json),
        )
        con.commit()
    finally:
        con.close()

    return QrScan(
        scan_id=scan_id,
        attribution_id=attribution_id,
        ts=datetime.fromisoformat(ts_iso.replace("Z", "+00:00")),
        meta_json=meta or {},
    )


def list_qr_scans(db_path: str, *, attribution_id: str, limit: int = 50) -> List[QrScan]:
    con = db.connect(db_path)
    try:
        rows = db.fetchall(
            con,
            "SELECT * FROM qr_scans WHERE attribution_id=? ORDER BY ts DESC LIMIT ?",
            (attribution_id, limit),
        )
        out: List[QrScan] = []
        for r in rows:
            out.append(QrScan(
                scan_id=r["scan_id"],
                attribution_id=r["attribution_id"],
                ts=datetime.fromisoformat(r["ts"].replace("Z", "+00:00")),
                meta_json=json.loads(r["meta_json"] or "{}"),
            ))
        return out
    finally:
        con.close()
