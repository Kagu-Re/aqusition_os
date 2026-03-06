from __future__ import annotations
from typing import Any, Dict, Type
from pydantic import BaseModel, ValidationError

from .errors import SchemaValidationError
from .framer_page_payload_v1 import FramerPagePayloadV1

_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "framer.page_payload.v1": FramerPagePayloadV1,
}

def supported() -> list[str]:
    return sorted(_SCHEMAS.keys())

def validate(schema: str, data: Dict[str, Any]) -> tuple[bool, Any | SchemaValidationError]:
    if schema not in _SCHEMAS:
        return False, SchemaValidationError(schema=schema, errors=[f"unknown_schema:{schema}"], raw=data)
    model = _SCHEMAS[schema]
    try:
        obj = model.model_validate(data)
        return True, obj
    except ValidationError as e:
        errs = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "invalid")
            errs.append(f"{loc}: {msg}")
        return False, SchemaValidationError(schema=schema, errors=errs, raw=data)
