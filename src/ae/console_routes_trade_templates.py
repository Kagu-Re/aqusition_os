"""API routes for trade templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from .console_support import require_secret
from .trade_templates import list_trade_templates, get_trade_template_preview
from .enums import Trade

router = APIRouter(prefix="/api/trade-templates", tags=["trade-templates"])


@router.get("")
def api_list_trade_templates(request: Request):
    """List all trade templates (trade, version, has_packages)."""
    require_secret(request)
    templates = list_trade_templates()
    items = [
        {
            "trade": t.trade.value,
            "version": t.version,
            "has_packages": len(t.default_packages) > 0,
        }
        for t in templates
    ]
    return {"count": len(items), "items": items}


@router.get("/{trade}")
def api_get_trade_template(
    request: Request,
    trade: str,
    geo: Optional[str] = "TH",
):
    """Get full template for a trade, with optional geo for price anchor preview."""
    require_secret(request)
    trade_str = trade.strip().lower()
    try:
        trade_enum = Trade(trade_str)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"trade_not_found: {trade}")
    data = get_trade_template_preview(trade_enum, geo=geo or "TH")
    return {"template": data}
