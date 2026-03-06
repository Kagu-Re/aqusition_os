from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class SchemaValidationError:
    schema: str
    errors: List[str]
    raw: Optional[object] = None
