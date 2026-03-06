from __future__ import annotations

from typing import Dict, Optional

from .models import ExportPreset

# Code-first presets (DB overrides supported)
PRESETS: Dict[str, ExportPreset] = {
    "leads_csv_basic": ExportPreset(name="leads_csv_basic", schema_name="leads_basic"),
}


def get_preset(name: str) -> Optional[ExportPreset]:
    return PRESETS.get(name)
