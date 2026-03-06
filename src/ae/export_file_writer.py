from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook

from .models import ExportPreset


def _format_value(v: Any, date_format: str) -> Any:
    if isinstance(v, datetime):
        return v.strftime(date_format)
    return v


def write_csv(path: str, rows: List[Dict[str, Any]], preset: ExportPreset) -> Tuple[str, int]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        keys = list(rows[0].keys()) if rows else []
        header_map = preset.header_map or {}
        headers = [header_map.get(k, k) for k in keys]
        w = csv.writer(f, delimiter=preset.delimiter or ",")
        w.writerow(headers)
        for r in rows:
            w.writerow([_format_value(r.get(k), preset.date_format) for k in keys])
    return path, len(rows)


def write_xlsx(path: str, rows: List[Dict[str, Any]], preset: ExportPreset) -> Tuple[str, int]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = preset.sheet_name or "export"
    keys = list(rows[0].keys()) if rows else []
    header_map = preset.header_map or {}
    ws.append([header_map.get(k, k) for k in keys])
    for r in rows:
        ws.append([_format_value(r.get(k), preset.date_format) for k in keys])
    wb.save(path)
    return path, len(rows)


def write_export_file(output_dir: str, filename: str, preset: ExportPreset, rows: List[Dict[str, Any]]) -> Tuple[str, int]:
    if preset.format not in ("csv", "xlsx"):
        raise ValueError(f"Unsupported export preset format: {preset.format}")
    ext = preset.format
    out_path = os.path.join(output_dir, f"{filename}.{ext}")
    if preset.format == "csv":
        return write_csv(out_path, rows, preset)
    return write_xlsx(out_path, rows, preset)
