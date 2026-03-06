from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .db import connect
from .models import ExportPreset


def upsert_export_preset(db_path: str, preset: ExportPreset) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO export_presets(name, preset_version, schema_name, format, delimiter, sheet_name, date_format, locale, header_map_json, enabled, updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(name) DO UPDATE SET
                preset_version=excluded.preset_version,
                schema_name=excluded.schema_name,
                format=excluded.format,
                delimiter=excluded.delimiter,
                sheet_name=excluded.sheet_name,
                date_format=excluded.date_format,
                locale=excluded.locale,
                header_map_json=excluded.header_map_json,
                enabled=excluded.enabled,
                updated_at=excluded.updated_at
            """,
            (
                preset.name,
                int(preset.preset_version),
                preset.schema_name,
                preset.format,
                preset.delimiter,
                preset.sheet_name,
                preset.date_format,
                preset.locale,
                json.dumps(preset.header_map or {}),
                1 if preset.enabled else 0,
                now,
            ),
        )
        conn.commit()


def get_export_preset(db_path: str, name: str) -> Optional[ExportPreset]:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT name, preset_version, schema_name, format, delimiter, sheet_name, date_format, locale, header_map_json, enabled, updated_at FROM export_presets WHERE name=?",
            (name,),
        ).fetchone()
    if not row:
        return None
    header_map = json.loads(row[8] or "{}")
    return ExportPreset(
        name=row[0],
        preset_version=int(row[1]),
        schema_name=row[2],
        format=row[3],
        delimiter=row[4] or ",",
        sheet_name=row[5] or "export",
        date_format=row[6] or "%Y-%m-%d %H:%M:%S",
        locale=row[7] or "en",
        header_map=header_map,
        enabled=bool(row[9]),
    )


def list_export_presets(db_path: str, limit: int = 200) -> List[Dict[str, Any]]:
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name, preset_version, schema_name, format, delimiter, sheet_name, date_format, locale, enabled, updated_at FROM export_presets ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "name": r[0],
            "preset_version": int(r[1]),
            "schema_name": r[2],
            "format": r[3],
            "delimiter": r[4],
            "sheet_name": r[5],
            "date_format": r[6],
            "locale": r[7],
            "enabled": bool(r[8]),
            "updated_at": r[9],
        }
        for r in rows
    ]
