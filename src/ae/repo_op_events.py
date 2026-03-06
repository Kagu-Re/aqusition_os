from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from pydantic import TypeAdapter

from . import db
from .models import OpEvent


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)


_op_event_adapter = TypeAdapter(OpEvent)


def insert_op_event(db_path: str, ev: OpEvent) -> None:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO op_events(
                   event_id, occurred_at, topic, schema_version,
                   aggregate_type, aggregate_id,
                   actor, correlation_id, causation_id,
                   payload_json
               ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                ev.event_id,
                ev.occurred_at.isoformat(),
                ev.topic,
                ev.schema_version,
                ev.aggregate_type,
                ev.aggregate_id,
                ev.actor,
                ev.correlation_id,
                ev.causation_id,
                json.dumps(ev.payload),
            ),
        )
        con.commit()
    finally:
        con.close()


def list_op_events(
    db_path: str,
    *,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 500,
    since: Optional[datetime] = None,
) -> List[OpEvent]:
    con = db.connect(db_path)
    try:
        sql = "SELECT * FROM op_events"
        where = []
        params: List[object] = []

        if aggregate_type is not None:
            where.append("aggregate_type=?")
            params.append(aggregate_type)
        if aggregate_id is not None:
            where.append("aggregate_id=?")
            params.append(aggregate_id)
        if correlation_id is not None:
            where.append("correlation_id=?")
            params.append(correlation_id)
        if topic is not None:
            where.append("topic=?")
            params.append(topic)
        if since is not None:
            where.append("occurred_at>=?")
            params.append(since.isoformat())

        if where:
            sql += " WHERE " + " AND ".join(where)

        sql += " ORDER BY occurred_at ASC"
        sql += " LIMIT ?"
        params.append(int(limit))

        rows = db.fetchall(con, sql, tuple(params))
        out: List[OpEvent] = []
        for row in rows:
            d = dict(row)
            d["occurred_at"] = _dt(d["occurred_at"])
            d["payload"] = json.loads(d["payload_json"])
            # Normalize names from SQL
            d.pop("payload_json", None)
            out.append(_op_event_adapter.validate_python(d))
        return out
    finally:
        con.close()


def get_op_event(db_path: str, event_id: str) -> OpEvent | None:
    con = db.connect(db_path)
    try:
        r = con.execute(
            """SELECT event_id, occurred_at, topic, schema_version,
                      aggregate_type, aggregate_id,
                      actor, correlation_id, causation_id,
                      payload_json
                 FROM op_events WHERE event_id=?""",
            (event_id,),
        ).fetchone()
        if not r:
            return None
        return _op_event_adapter.validate_python(
            {
                "event_id": r[0],
                "occurred_at": _dt(r[1]),
                "topic": r[2],
                "schema_version": r[3],
                "aggregate_type": r[4],
                "aggregate_id": r[5],
                "actor": r[6],
                "correlation_id": r[7],
                "causation_id": r[8],
                "payload": json.loads(r[9] or "{}"),
            }
        )
    finally:
        con.close()
