"""Client service functions for applying trade templates and auto-population."""

from __future__ import annotations

from typing import List
from .models import Client, ServicePackage
from .enums import BusinessModel
from .trade_templates import (
    get_trade_template_or_fallback,
    format_price_anchor,
    DEFAULT_PRICE_RANGES,
)
from .repo_service_packages import get_package, list_packages
from datetime import datetime
import re


def _slugify(text: str) -> str:
    """Convert text to slug format."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text


def apply_trade_template_to_client(client: Client, overwrite: bool = False) -> Client:
    """Apply trade template defaults to client (Tier 2 fields).
    
    When overwrite=False, only populates fields that are None/empty.
    When overwrite=True, always applies template defaults (for reapply).
    Returns enhanced client with defaults applied.
    """
    template = get_trade_template_or_fallback(client.trade)

    if overwrite or not client.hours:
        client.hours = template.default_hours
    if overwrite or not client.license_badges:
        client.license_badges = template.default_license_badges.copy()
    if overwrite or not client.price_anchor:
        client.price_anchor = format_price_anchor(template, client.geo_country)
    if overwrite or not client.brand_theme:
        client.brand_theme = template.default_brand_theme

    return client


def generate_default_service_config(client: Client, overwrite: bool = False) -> dict:
    """Generate default service_config_json from trade template patterns.

    Replaces placeholders: {service_area[0]}, {price_anchor}, {hours}, {client_name}
    When overwrite=False, only sets default_* when custom_* is not set.
    When overwrite=True, always sets default_* from template (for reapply).
    """
    template = get_trade_template_or_fallback(client.trade)
    config = client.service_config_json.copy() if client.service_config_json else {}

    def replace_placeholders(text: str) -> str:
        result = text
        if "{service_area[0]}" in result and client.service_area:
            result = result.replace("{service_area[0]}", client.service_area[0])
        if "{price_anchor}" in result and client.price_anchor:
            result = result.replace("{price_anchor}", client.price_anchor)
        if "{hours}" in result and client.hours:
            result = result.replace("{hours}", client.hours)
        if "{client_name}" in result and client.client_name:
            result = result.replace("{client_name}", client.client_name)
        return result

    if overwrite or "custom_testimonials" not in config or not config.get("custom_testimonials"):
        testimonials = [replace_placeholders(p) for p in template.default_testimonials_patterns]
        config["default_testimonials"] = testimonials
    if overwrite or "custom_faq" not in config or not config.get("custom_faq"):
        faq = [replace_placeholders(p) for p in template.default_faq_patterns]
        config["default_faq"] = faq
    if overwrite or "custom_amenities" not in config or not config.get("custom_amenities"):
        config["default_amenities"] = template.default_amenities.copy()
    if overwrite or "custom_cta_primary" not in config or not config.get("custom_cta_primary"):
        config["default_cta_primary"] = template.default_cta_primary
    if overwrite or "custom_cta_secondary" not in config or not config.get("custom_cta_secondary"):
        config["default_cta_secondary"] = template.default_cta_secondary

    # Placeholder for GBP/manual reviews; populated by sync or console. On overwrite, reset.
    if overwrite:
        config["reviews"] = []
    else:
        config.setdefault("reviews", [])

    return config


def create_default_packages_from_template(db_path: str, client: Client) -> List[ServicePackage]:
    """Create default service packages from trade template for fixed_price clients.
    
    Only creates packages if:
    1. business_model == fixed_price
    2. No packages exist for this client yet (idempotent)
    
    Returns list of created packages.
    """
    if client.business_model != BusinessModel.fixed_price:
        return []
    
    # Check if packages already exist
    existing_packages = list_packages(db_path, client_id=client.client_id, active=True, limit=1)
    if existing_packages:
        return []  # Already has packages, don't create defaults
    
    template = get_trade_template_or_fallback(client.trade)
    if not template.default_packages:
        return []  # No default packages in template

    geo = (client.geo_country or "TH").upper()
    base_price = DEFAULT_PRICE_RANGES.get(template.trade.value, {}).get(
        geo
    ) or DEFAULT_PRICE_RANGES.get(template.trade.value, {}).get("TH") or 100
    first_template_price = template.default_packages[0].get("price") or base_price

    created_packages = []
    now = datetime.utcnow()

    for idx, pkg_data in enumerate(template.default_packages):
        name_slug = _slugify(pkg_data["name"])
        package_id = f"pkg-{client.client_id}-{name_slug}"

        existing = get_package(db_path, package_id)
        if existing:
            continue

        template_price = pkg_data.get("price") or base_price
        geo_price = round(base_price * (template_price / first_template_price))
        meta = dict(pkg_data.get("meta_json") or {})
        meta["source_template"] = template.trade.value
        meta["template_package_idx"] = idx

        package = ServicePackage(
            package_id=package_id,
            client_id=client.client_id,
            name=pkg_data["name"],
            price=float(geo_price),
            duration_min=pkg_data["duration_min"],
            addons=pkg_data.get("addons", []),
            active=True,
            meta_json=meta,
            created_at=now,
            updated_at=now,
        )
        
        from .repo_service_packages import create_package
        create_package(db_path, package)
        created_packages.append(package)
    
    return created_packages


def sync_packages_from_template(
    db_path: str, client_id: str, overwrite: bool = False
) -> List[ServicePackage]:
    """Sync packages from trade template for a client.

    When overwrite=False (merge): only create packages that don't exist.
    When overwrite=True: delete existing packages first, then create from template.
    Returns list of created packages.
    """
    from . import repo
    client = repo.get_client(db_path, client_id=client_id)
    if not client:
        raise ValueError(f"client_not_found: {client_id}")
    if overwrite:
        existing = list_packages(db_path, client_id=client_id, limit=500)
        for pkg in existing:
            from .repo_service_packages import delete_package
            delete_package(db_path, pkg.package_id)
    return create_default_packages_from_template(db_path, client)
