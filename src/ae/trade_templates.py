"""Trade template registry for auto-populating client defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, TypedDict
from .models import TradeTemplate
from .enums import Trade


class DefaultPackageSchema(TypedDict, total=False):
    """Schema for default_packages items in TradeTemplate. name, price, duration_min required."""
    name: str
    price: float
    duration_min: int
    addons: List[str]
    meta_json: Dict[str, Any]


def _get_trades_dir() -> Path:
    """Resolve path to trades config directory. AE_TRADES_CONFIG_PATH overrides default."""
    env_path = os.getenv("AE_TRADES_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        # If env points to a file (legacy), use its parent as dir
        return p.parent if p.suffix == ".json" else p
    # Default: config/trades/ relative to project root (parent of src/)
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "config" / "trades"


def _load_trade_file(path: Path) -> Dict[str, Any]:
    """Load a single JSON file."""
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def _load_trades_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load trades config. Returns merged structure with "trades", "currency_map", "price_ranges".
    - If path is a file: load single legacy trades.json (backward compat).
    - If path is a directory or None: load _defaults.json + per-trade files from config/trades/.
    """
    base = path or _get_trades_dir()
    if base.is_file():
        # Legacy single-file mode
        data = _load_trade_file(base)
        if "trades" not in data:
            raise ValueError("Trades config must contain 'trades' key")
        return data

    # Per-trade directory layout
    if not base.is_dir():
        raise FileNotFoundError(
            f"Trades config dir not found: {base}. Set AE_TRADES_CONFIG_PATH to override."
        )
    defaults_path = base / "_defaults.json"
    if not defaults_path.exists():
        raise FileNotFoundError(f"Trades defaults not found: {defaults_path}")

    defaults = _load_trade_file(defaults_path)
    currency_map = defaults.get("currency_map") or {}
    price_ranges = defaults.get("price_ranges") or {}

    generic_path = base / "generic.json"
    if not generic_path.exists():
        raise FileNotFoundError(f"Trades generic fallback not found: {generic_path}")
    generic_data = _load_trade_file(generic_path)

    trades_data: Dict[str, Dict[str, Any]] = {"generic": generic_data}
    for trade in Trade:
        key = trade.value
        trade_path = base / f"{key}.json"
        if trade_path.exists():
            trades_data[key] = _load_trade_file(trade_path)

    return {
        "currency_map": currency_map,
        "price_ranges": price_ranges,
        "trades": trades_data,
    }


def _build_trade_templates() -> Dict[Trade, TradeTemplate]:
    """Build registry from config. Call once at module load."""
    config = _load_trades_config()
    trades_data = config["trades"]
    generic_data = trades_data.get("generic")
    if not generic_data:
        raise ValueError("Trades config must contain 'generic' fallback")

    result: Dict[Trade, TradeTemplate] = {}
    for trade in Trade:
        key = trade.value
        data = trades_data.get(key)
        if data:
            obj = TradeTemplate.model_validate({"trade": trade, **data})
            result[trade] = obj
        else:
            generic = TradeTemplate.model_validate({"trade": trade, **generic_data})
            result[trade] = generic

    return result


def _get_currency_map() -> Dict[str, str]:
    """Load currency map from config."""
    config = _load_trades_config()
    return config.get("currency_map") or {
        "AU": "A$", "US": "$", "TH": "฿", "GB": "£", "EU": "€", "CA": "C$", "NZ": "NZ$",
    }


def _get_price_ranges() -> Dict[str, Dict[str, int]]:
    """Load price ranges from config."""
    config = _load_trades_config()
    return config.get("price_ranges") or {}


# Load registry at import
_TRADE_TEMPLATES = _build_trade_templates()
CURRENCY_MAP = _get_currency_map()
DEFAULT_PRICE_RANGES = _get_price_ranges()


def _get_price_for_trade(trade: Trade, geo_country: str) -> int:
    """Get default price for trade and geo."""
    trade_key = trade.value
    geo_key = geo_country.upper()
    if trade_key in DEFAULT_PRICE_RANGES and geo_key in DEFAULT_PRICE_RANGES[trade_key]:
        return DEFAULT_PRICE_RANGES[trade_key][geo_key]
    # Fallback to first available price or default
    if trade_key in DEFAULT_PRICE_RANGES:
        prices = DEFAULT_PRICE_RANGES[trade_key]
        return list(prices.values())[0] if prices else 100
    return 100


def _get_currency(geo_country: str) -> str:
    """Get currency symbol for country."""
    return CURRENCY_MAP.get(geo_country.upper(), "$")


def get_trade_template(trade: Trade) -> Optional[TradeTemplate]:
    """Get trade template for a given trade, or None if not found."""
    return _TRADE_TEMPLATES.get(trade)


def get_trade_template_or_fallback(trade: Trade) -> TradeTemplate:
    """Get trade template or return generic fallback."""
    template = get_trade_template(trade)
    if template:
        return template
    # Should not happen when config is valid; use generic-based copy as last resort
    generic_template = _TRADE_TEMPLATES.get(Trade.plumber)  # generic config used for missing keys
    copy = generic_template.model_copy()
    copy.trade = trade
    return copy


def format_price_anchor(template: TradeTemplate, geo_country: str) -> str:
    """Format price anchor from template pattern using trade and geo."""
    price = _get_price_for_trade(template.trade, geo_country)
    currency = _get_currency(geo_country)
    return template.default_price_anchor_pattern.format(currency=currency, amount=price)


def list_trade_templates() -> List[TradeTemplate]:
    """Return all registered trade templates."""
    return list(_TRADE_TEMPLATES.values())


def get_trade_template_preview(trade: Trade, geo: str = "TH") -> Dict[str, Any]:
    """Return template as dict with formatted price anchor for preview/API."""
    template = get_trade_template_or_fallback(trade)
    data = template.model_dump()
    data["price_anchor_formatted"] = format_price_anchor(template, geo)
    return data
