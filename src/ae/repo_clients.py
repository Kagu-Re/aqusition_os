from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import TypeAdapter

from . import db
from .models import (
    Client, Template, Page, WorkItem, PublishLog, ChangeLog, EventRecord, BulkOp, AdStat
)
from .enums import PageStatus, WorkStatus, PublishAction, LogResult
from .client_service import (
    apply_trade_template_to_client,
    generate_default_service_config,
    create_default_packages_from_template
)

def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)

_client_adapter = TypeAdapter(Client)

def upsert_client(db_path: str, client: Client, apply_defaults: bool = True) -> None:
    """Upsert client with optional auto-population of defaults from trade template.
    
    Args:
        db_path: Database path
        client: Client to upsert
        apply_defaults: If True, auto-populate Tier 2 fields and service_config_json from trade template
    """
    # Apply trade template defaults if requested
    if apply_defaults:
        client = apply_trade_template_to_client(client)
        
        # Generate default service_config_json if not already populated
        if not client.service_config_json or not any(
            key.startswith("custom_") or key.startswith("default_")
            for key in client.service_config_json.keys()
        ):
            client.service_config_json = generate_default_service_config(client)
    
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO clients(client_id, client_name, trade, business_model, geo_country, geo_city, service_area_json,
                                      primary_phone, lead_email, status, hours, license_badges_json, price_anchor, brand_theme, notes_internal, service_config_json)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(client_id) DO UPDATE SET
                    client_name=excluded.client_name,
                    trade=excluded.trade,
                    business_model=excluded.business_model,
                    geo_country=excluded.geo_country,
                    geo_city=excluded.geo_city,
                    service_area_json=excluded.service_area_json,
                    primary_phone=excluded.primary_phone,
                    lead_email=excluded.lead_email,
                    status=excluded.status,
                    hours=excluded.hours,
                    license_badges_json=excluded.license_badges_json,
                    price_anchor=excluded.price_anchor,
                    brand_theme=excluded.brand_theme,
                    notes_internal=excluded.notes_internal,
                    service_config_json=excluded.service_config_json
            """,
            (
                client.client_id, client.client_name, client.trade.value, client.business_model.value, client.geo_country, client.geo_city,
                json.dumps(client.service_area),
                client.primary_phone, str(client.lead_email), client.status.value,
                client.hours, json.dumps(client.license_badges), client.price_anchor, client.brand_theme, client.notes_internal,
                json.dumps(client.service_config_json)
            )
        )
        con.commit()
        
        # Create default packages for fixed_price clients (only if new client or no packages exist)
        if apply_defaults:
            create_default_packages_from_template(db_path, client)
    finally:
        con.close()

def get_client(db_path: str, client_id: str) -> Optional[Client]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM clients WHERE client_id=?", (client_id,))
        if not row:
            return None
        d = dict(row)
        d["service_area"] = json.loads(d.pop("service_area_json", "[]"))
        d["license_badges"] = json.loads(d.pop("license_badges_json", "[]"))
        d["service_config_json"] = json.loads(d.pop("service_config_json", "{}"))
        # Handle missing business_model for existing records (default to quote_based)
        if "business_model" not in d or not d["business_model"]:
            d["business_model"] = "quote_based"
        d["trade"] = d["trade"]
        d["status"] = d["status"]
        return _client_adapter.validate_python(d)
    finally:
        con.close()

def set_client_status(db_path: str, client_id: str, status: str) -> Client:
    status = (status or "").strip().lower()
    if status not in ("draft", "qa", "live", "paused", "archived"):
        raise ValueError("status must be draft|active|paused|archived")

    con = db.connect(db_path)
    try:
        cur = con.execute("UPDATE clients SET status=? WHERE client_id=?", (status, client_id))
        if cur.rowcount == 0:
            raise ValueError(f"client not found: {client_id}")
        con.commit()
        c = get_client(db_path, client_id=client_id)
        if not c:
            raise ValueError(f"client not found: {client_id}")
        return c
    finally:
        con.close()

