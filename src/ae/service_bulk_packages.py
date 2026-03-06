"""Bulk operations for service packages."""

from __future__ import annotations

from typing import List
from datetime import datetime

from . import repo
from .models import BulkOp


def _resolve_bulk_package_targets(
    db_path: str,
    selector: dict,
) -> list[str]:
    """Resolve selector_json to a list of package_ids.
    
    Supported keys:
    - package_ids: explicit list
    - client_id
    - active (bool)
    - limit
    """
    if selector.get("package_ids"):
        return list(selector["package_ids"])
    
    client_id = selector.get("client_id")
    active = selector.get("active")
    if active is not None:
        active = bool(active)
    limit = int(selector.get("limit") or 200)
    
    packages = repo.list_packages_filtered(
        db_path,
        package_ids=None,
        client_id=client_id,
        active=active,
        limit=limit,
    )
    return [p.package_id for p in packages]


def run_bulk_update_packages(
    db_path: str,
    package_ids: List[str] | None = None,
    client_id: str | None = None,
    active: bool | None = None,
    limit: int = 200,
    mode: str = "dry_run",
    updates: dict | None = None,
    notes: str | None = None,
) -> BulkOp:
    """Bulk update service packages.
    
    Args:
        db_path: Database path
        package_ids: Explicit list of package IDs (optional)
        client_id: Filter by client ID (optional)
        active: Filter by active status (optional)
        limit: Maximum packages to update
        mode: 'dry_run' or 'execute'
        updates: Dict with update fields:
            - 'active': bool - Set active status
            - 'price': float - Set price
        notes: Optional notes for the operation
    
    Returns:
        BulkOp with results
    """
    import uuid
    
    if not updates:
        raise ValueError("updates dict is required with at least one field (active or price)")
    
    if "active" not in updates and "price" not in updates:
        raise ValueError("updates must contain 'active' or 'price'")
    
    bulk_id = f"bulk_{uuid.uuid4().hex[:12]}"
    selector = {"limit": limit}
    if package_ids:
        selector["package_ids"] = package_ids
    if client_id:
        selector["client_id"] = client_id
    if active is not None:
        selector["active"] = active
    
    # Determine action name
    if "active" in updates and "price" in updates:
        action = "bulk_update_packages_active_price"
    elif "active" in updates:
        action = "bulk_update_packages_active"
    else:
        action = "bulk_update_packages_price"
    
    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action=action,
        selector_json=selector,
        status="queued",
        result_json={
            "packages": [],
            "counters": {
                "total": 0,
                "updated": 0,
                "skipped": 0,
                "failed": 0,
            },
            "updates": updates,
        },
        notes=notes,
    )
    repo.insert_bulk_op(db_path, op)
    
    if not repo.try_claim_bulk_op(db_path, bulk_id):
        repo.update_bulk_op(db_path, bulk_id, "failed", {"error": "bulk_op_not_claimed"})
        op.status = "failed"
        try:
            repo.append_activity(
                db_path,
                action="bulk_update_packages",
                entity_type="bulk_op",
                entity_id=str(op.bulk_id),
                actor="system",
                details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
            )
        except Exception:
            pass
        return op
    
    targets = _resolve_bulk_package_targets(db_path, selector)
    result = op.result_json
    result["counters"]["total"] = len(targets)
    repo.update_bulk_op(db_path, bulk_id, "running", result)
    
    for package_id in targets:
        try:
            existing = repo.get_package(db_path, package_id)
            if not existing:
                result["packages"].append({"package_id": package_id, "status": "failed", "reason": "package_not_found"})
                result["counters"]["failed"] += 1
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue
            
            # Check if update is needed
            needs_update = False
            if "active" in updates and existing.active != updates["active"]:
                needs_update = True
            if "price" in updates and existing.price != updates["price"]:
                needs_update = True
            
            if not needs_update:
                result["packages"].append({"package_id": package_id, "status": "skipped", "reason": "no_change_needed"})
                result["counters"]["skipped"] += 1
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue
            
            if mode == "dry_run":
                result["packages"].append({
                    "package_id": package_id,
                    "status": "would_update",
                    "current": {
                        "active": existing.active,
                        "price": existing.price,
                    },
                    "updates": updates,
                })
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue
            
            # Execute update
            if "active" in updates:
                repo.bulk_update_active(db_path, [package_id], updates["active"])
            if "price" in updates:
                repo.bulk_update_price(db_path, [package_id], updates["price"])
            
            result["packages"].append({
                "package_id": package_id,
                "status": "updated",
                "updates": updates,
            })
            result["counters"]["updated"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            
        except Exception as e:
            result["packages"].append({
                "package_id": package_id,
                "status": "failed",
                "error": str(e),
            })
            result["counters"]["failed"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
    
    repo.update_bulk_op(db_path, bulk_id, "done", result)
    op.status = "done"
    op.result_json = result
    op.updated_at = datetime.utcnow()
    
    # activity log (append-only)
    try:
        repo.append_activity(
            db_path,
            action="bulk_update_packages",
            entity_type="bulk_op",
            entity_id=str(op.bulk_id),
            actor="system",
            details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
        )
    except Exception:
        pass
    return op


def run_bulk_delete_packages(
    db_path: str,
    package_ids: List[str] | None = None,
    client_id: str | None = None,
    active: bool | None = None,
    limit: int = 200,
    mode: str = "dry_run",
    notes: str | None = None,
) -> BulkOp:
    """Bulk delete service packages.
    
    Args:
        db_path: Database path
        package_ids: Explicit list of package IDs (optional)
        client_id: Filter by client ID (optional)
        active: Filter by active status (optional)
        limit: Maximum packages to delete
        mode: 'dry_run' or 'execute'
        notes: Optional notes for the operation
    
    Returns:
        BulkOp with results
    """
    import uuid
    
    bulk_id = f"bulk_{uuid.uuid4().hex[:12]}"
    selector = {"limit": limit}
    if package_ids:
        selector["package_ids"] = package_ids
    if client_id:
        selector["client_id"] = client_id
    if active is not None:
        selector["active"] = active
    
    op = BulkOp(
        bulk_id=bulk_id,
        mode=mode,
        action="bulk_delete_packages",
        selector_json=selector,
        status="queued",
        result_json={
            "packages": [],
            "counters": {
                "total": 0,
                "deleted": 0,
                "skipped": 0,
                "failed": 0,
            },
        },
        notes=notes,
    )
    repo.insert_bulk_op(db_path, op)
    
    if not repo.try_claim_bulk_op(db_path, bulk_id):
        repo.update_bulk_op(db_path, bulk_id, "failed", {"error": "bulk_op_not_claimed"})
        op.status = "failed"
        try:
            repo.append_activity(
                db_path,
                action="bulk_delete_packages",
                entity_type="bulk_op",
                entity_id=str(op.bulk_id),
                actor="system",
                details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
            )
        except Exception:
            pass
        return op
    
    targets = _resolve_bulk_package_targets(db_path, selector)
    result = op.result_json
    result["counters"]["total"] = len(targets)
    repo.update_bulk_op(db_path, bulk_id, "running", result)
    
    for package_id in targets:
        try:
            existing = repo.get_package(db_path, package_id)
            if not existing:
                result["packages"].append({"package_id": package_id, "status": "failed", "reason": "package_not_found"})
                result["counters"]["failed"] += 1
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue
            
            if mode == "dry_run":
                result["packages"].append({
                    "package_id": package_id,
                    "status": "would_delete",
                    "name": existing.name,
                    "client_id": existing.client_id,
                })
                repo.update_bulk_op(db_path, bulk_id, "running", result)
                continue
            
            repo.delete_package(db_path, package_id)
            result["packages"].append({
                "package_id": package_id,
                "status": "deleted",
            })
            result["counters"]["deleted"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
            
        except Exception as e:
            result["packages"].append({
                "package_id": package_id,
                "status": "failed",
                "error": str(e),
            })
            result["counters"]["failed"] += 1
            repo.update_bulk_op(db_path, bulk_id, "running", result)
    
    repo.update_bulk_op(db_path, bulk_id, "done", result)
    op.status = "done"
    op.result_json = result
    op.updated_at = datetime.utcnow()
    
    # activity log (append-only)
    try:
        repo.append_activity(
            db_path,
            action="bulk_delete_packages",
            entity_type="bulk_op",
            entity_id=str(op.bulk_id),
            actor="system",
            details={"mode": op.mode, "status": op.status, "counters": op.result_json.get("counters", {})},
        )
    except Exception:
        pass
    return op
