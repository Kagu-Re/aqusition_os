from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from .db import connect, init_db
from .models import ExportSchema


def upsert_export_schema(db_path: str, schema: ExportSchema, *, updated_at: str | None = None) -> None:
    """Upsert an export schema override.

    Stores the schema as JSON. Runtime resolution should prefer DB override when present.
    """
    init_db(db_path)
    ts = updated_at or datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    payload = schema.model_dump()
    with connect(db_path) as conn:
        conn.execute(
            """INSERT INTO export_schemas (name, schema_version, schema_json, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 schema_version=excluded.schema_version,
                 schema_json=excluded.schema_json,
                 updated_at=excluded.updated_at
            """,
            (schema.name, int(schema.schema_version), json.dumps(payload), ts),
        )
        conn.commit()


def get_export_schema(db_path: str, name: str) -> Optional[ExportSchema]:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT schema_json FROM export_schemas WHERE name = ?",
            (name,),
        ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0] or "{}")
    except Exception:
        return None
    try:
        return ExportSchema(**data)
    except Exception:
        return None


def list_export_schemas(db_path: str, *, limit: int = 200) -> list[dict[str, Any]]:
    """List schema overrides stored in DB (metadata only)."""
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name, schema_version, updated_at FROM export_schemas ORDER BY updated_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [
        {"name": r[0], "schema_version": int(r[1]), "updated_at": r[2]}
        for r in rows
    ]
