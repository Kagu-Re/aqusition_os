from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import db
from .models import ServicePackage


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def create_package(db_path: str, package: ServicePackage) -> ServicePackage:
    """Create a new service package."""
    db.init_db(db_path)
    created_at = package.created_at or _now()
    updated_at = _now()
    addons_json = json.dumps(package.addons or [], ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(package.meta_json or {}, ensure_ascii=False, separators=(",", ":"))
    
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO service_packages(
                package_id, client_id, name, price, duration_min, addons_json, active, meta_json, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                package.package_id,
                package.client_id,
                package.name,
                package.price,
                package.duration_min,
                addons_json,
                1 if package.active else 0,
                meta_json,
                created_at,
                updated_at,
            ),
        )
        con.commit()
    finally:
        con.close()
    
    return ServicePackage(
        package_id=package.package_id,
        client_id=package.client_id,
        name=package.name,
        price=package.price,
        duration_min=package.duration_min,
        addons=package.addons or [],
        active=package.active,
        meta_json=package.meta_json or {},
        created_at=created_at,
        updated_at=updated_at,
    )


def get_package(db_path: str, package_id: str) -> Optional[ServicePackage]:
    """Get a service package by ID."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM service_packages WHERE package_id=?", (package_id,))
        if not row:
            return None
        return ServicePackage(
            package_id=row["package_id"],
            client_id=row["client_id"],
            name=row["name"],
            price=row["price"],
            duration_min=row["duration_min"],
            addons=json.loads(row["addons_json"] or "[]"),
            active=bool(row["active"]),
            meta_json=json.loads(row["meta_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    finally:
        con.close()


def list_packages(
    db_path: str,
    *,
    client_id: Optional[str] = None,
    active: Optional[bool] = None,
    limit: int = 50,
) -> List[ServicePackage]:
    """List service packages with optional filters."""
    db.init_db(db_path)
    sql = "SELECT * FROM service_packages"
    params: List[Any] = []
    where: List[str] = []
    
    if client_id:
        where.append("client_id=?")
        params.append(client_id)
    
    if active is not None:
        where.append("active=?")
        params.append(1 if active else 0)
    
    if where:
        sql += " WHERE " + " AND ".join(where)
    
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[ServicePackage] = []
        for r in rows:
            out.append(ServicePackage(
                package_id=r["package_id"],
                client_id=r["client_id"],
                name=r["name"],
                price=r["price"],
                duration_min=r["duration_min"],
                addons=json.loads(r["addons_json"] or "[]"),
                active=bool(r["active"]),
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            ))
        return out
    finally:
        con.close()


def update_package(db_path: str, package: ServicePackage) -> ServicePackage:
    """Update an existing service package."""
    db.init_db(db_path)
    updated_at = _now()
    addons_json = json.dumps(package.addons or [], ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(package.meta_json or {}, ensure_ascii=False, separators=(",", ":"))
    
    con = db.connect(db_path)
    try:
        # Get existing created_at
        existing = db.fetchone(con, "SELECT created_at FROM service_packages WHERE package_id=?", (package.package_id,))
        created_at = existing["created_at"] if existing else updated_at
        
        con.execute(
            """UPDATE service_packages SET
                client_id=?, name=?, price=?, duration_min=?, addons_json=?, active=?, meta_json=?, updated_at=?
            WHERE package_id=?""",
            (
                package.client_id,
                package.name,
                package.price,
                package.duration_min,
                addons_json,
                1 if package.active else 0,
                meta_json,
                updated_at,
                package.package_id,
            ),
        )
        con.commit()
    finally:
        con.close()
    
    return ServicePackage(
        package_id=package.package_id,
        client_id=package.client_id,
        name=package.name,
        price=package.price,
        duration_min=package.duration_min,
        addons=package.addons or [],
        active=package.active,
        meta_json=package.meta_json or {},
        created_at=datetime.fromisoformat(created_at),
        updated_at=updated_at,
    )


def delete_package(db_path: str, package_id: str) -> None:
    """Delete a service package."""
    db.init_db(db_path)
    con = db.connect(db_path)
    try:
        con.execute("DELETE FROM service_packages WHERE package_id=?", (package_id,))
        con.commit()
    finally:
        con.close()


def list_packages_filtered(
    db_path: str,
    *,
    package_ids: Optional[List[str]] = None,
    client_id: Optional[str] = None,
    active: Optional[bool] = None,
    limit: int = 200,
) -> List[ServicePackage]:
    """List service packages with filters for bulk operations.
    
    Similar to list_packages but supports explicit package_ids list.
    """
    db.init_db(db_path)
    
    # If explicit IDs provided, use them
    if package_ids:
        if len(package_ids) > limit:
            package_ids = package_ids[:limit]
        placeholders = ",".join("?" * len(package_ids))
        sql = f"SELECT * FROM service_packages WHERE package_id IN ({placeholders}) ORDER BY updated_at DESC"
        params: List[Any] = list(package_ids)
    else:
        # Use filters
        sql = "SELECT * FROM service_packages"
        params: List[Any] = []
        where: List[str] = []
        
        if client_id:
            where.append("client_id=?")
            params.append(client_id)
        
        if active is not None:
            where.append("active=?")
            params.append(1 if active else 0)
        
        if where:
            sql += " WHERE " + " AND ".join(where)
        
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
    
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[ServicePackage] = []
        for r in rows:
            out.append(ServicePackage(
                package_id=r["package_id"],
                client_id=r["client_id"],
                name=r["name"],
                price=r["price"],
                duration_min=r["duration_min"],
                addons=json.loads(r["addons_json"] or "[]"),
                active=bool(r["active"]),
                meta_json=json.loads(r["meta_json"] or "{}"),
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"]),
            ))
        return out
    finally:
        con.close()


def bulk_update_active(
    db_path: str,
    package_ids: List[str],
    active: bool,
) -> int:
    """Bulk update active status for multiple packages.
    
    Returns count of packages updated.
    """
    db.init_db(db_path)
    updated_at = _now()
    
    con = db.connect(db_path)
    try:
        placeholders = ",".join("?" * len(package_ids))
        sql = f"UPDATE service_packages SET active=?, updated_at=? WHERE package_id IN ({placeholders})"
        params = [1 if active else 0, updated_at] + list(package_ids)
        con.execute(sql, tuple(params))
        con.commit()
        return con.rowcount
    finally:
        con.close()


def bulk_update_price(
    db_path: str,
    package_ids: List[str],
    price: float,
) -> int:
    """Bulk update price for multiple packages.
    
    Returns count of packages updated.
    """
    db.init_db(db_path)
    updated_at = _now()
    
    con = db.connect(db_path)
    try:
        placeholders = ",".join("?" * len(package_ids))
        sql = f"UPDATE service_packages SET price=?, updated_at=? WHERE package_id IN ({placeholders})"
        params = [price, updated_at] + list(package_ids)
        con.execute(sql, tuple(params))
        con.commit()
        return con.rowcount
    finally:
        con.close()


def bulk_delete_packages(
    db_path: str,
    package_ids: List[str],
) -> int:
    """Bulk delete multiple packages.
    
    Returns count of packages deleted.
    """
    db.init_db(db_path)
    
    con = db.connect(db_path)
    try:
        placeholders = ",".join("?" * len(package_ids))
        sql = f"DELETE FROM service_packages WHERE package_id IN ({placeholders})"
        con.execute(sql, tuple(package_ids))
        con.commit()
        return con.rowcount
    finally:
        con.close()
