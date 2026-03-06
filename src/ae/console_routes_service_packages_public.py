from __future__ import annotations
from fastapi import APIRouter, Request, HTTPException
from typing import Optional, Dict, Any
from .console_support import _resolve_db_path
from .tenant import get_scoped_client_id
from .api_keys import resolve_tenant_for_public_request, ensure_api_key_or_401
from .public_guard import rate_limit_or_429
from . import repo
from .repo_booking_requests import list_booking_requests

public_router = APIRouter()


def _calculate_availability_for_package(
    db_path: str,
    package_id: str,
    package_meta_json: Dict[str, Any]
) -> Optional[int]:
    """Calculate available slots for a package from Money Board booking data.
    
    Returns:
    - None if max_capacity not set or calculation not applicable
    - Integer representing available slots (max_capacity - active_bookings)
    """
    # Get max_capacity from package meta_json
    max_capacity = package_meta_json.get("max_capacity")
    if max_capacity is None:
        # Check if available_slots is explicitly set
        explicit_slots = package_meta_json.get("available_slots")
        return explicit_slots if explicit_slots is not None else None
    
    # Count active bookings for this package
    # Active states: confirmed, deposit_requested, time_window_set
    active_states = ["confirmed", "deposit_requested", "time_window_set"]
    all_bookings = list_booking_requests(db_path, limit=1000)
    
    active_bookings = sum(
        1 for br in all_bookings
        if br.package_id == package_id and br.status in active_states
    )
    
    available_slots = max(0, max_capacity - active_bookings)
    return available_slots


@public_router.get("/v1/service-packages")
def list_service_packages_public(
    request: Request,
    client_id: Optional[str] = None,
    active: Optional[bool] = True,
    limit: int = 50,
    page_id: Optional[str] = None,
    service_focus: Optional[str] = None,
):
    """Public endpoint to list active service packages for a client.
    
    Used by landing pages to display available packages.
    Includes availability calculation from Money Board booking data.
    Can filter packages by service_focus if page_id or service_focus is provided.
    No authentication required - rate limited only.
    When multi-tenant: uses X-Tenant-ID as client_id if client_id not in query.
    If both client_id and X-Tenant-ID provided, they must match.
    """
    rate_limit_or_429(request)
    resolve_tenant_for_public_request(request)
    ensure_api_key_or_401(request)
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    scoped = get_scoped_client_id(request)
    effective_client_id = client_id
    if scoped:
        if client_id and client_id != scoped:
            raise HTTPException(status_code=403, detail="client_id must match X-Tenant-ID when multi-tenant")
        effective_client_id = scoped
    if not effective_client_id:
        raise HTTPException(status_code=400, detail="client_id required (or X-Tenant-ID when multi-tenant)")
    
    # Get service_focus from page if page_id provided
    if page_id and not service_focus:
        page = repo.get_page(db_path, page_id)
        if page:
            service_focus = page.service_focus
    
    # Only return active packages for the specified client
    packages = repo.list_packages(
        db_path, 
        client_id=effective_client_id, 
        active=active, 
        limit=limit
    )
    
    # Get client for fallback default_available_slots
    client = repo.get_client(db_path, effective_client_id)
    client_default_slots = None
    if client and hasattr(client, "service_config_json"):
        client_config = client.service_config_json or {}
        client_default_slots = client_config.get("default_available_slots")
    
    # Enhance packages with availability data and filter by service_focus
    enhanced_items = []
    for pkg in packages:
        pkg_dict = pkg.model_dump()
        meta_json = pkg_dict.get("meta_json", {}) or {}
        
        # Filter by service_focus if specified
        # Packages can have service_focus in meta_json to indicate which pages they belong to
        # Logic:
        # - Premium page (service_focus="premium"): ONLY show packages with package_focus="premium"
        # - Express page (service_focus="express"): ONLY show packages with package_focus="express"
        # - Main page (service_focus=None): ONLY show packages with package_focus=None or missing
        if service_focus:
            package_focus = meta_json.get("service_focus")
            # Only include packages where package_focus matches the page's service_focus
            # Packages with package_focus=None are excluded from premium/express pages
            if package_focus != service_focus:
                continue
        else:
            # For main page (service_focus=None), show ALL packages
            # This allows main pages to show all available packages regardless of service_focus
            # (Previously filtered out packages with service_focus, but that's too restrictive)
            pass  # Don't filter - show all packages
        
        # Calculate availability from Money Board if max_capacity is set
        # Otherwise use explicit available_slots from meta_json
        available_slots = _calculate_availability_for_package(
            db_path,
            pkg.package_id,
            meta_json
        )
        
        # If calculated availability is None, check for explicit value in package
        if available_slots is None:
            available_slots = meta_json.get("available_slots")
        
        # Fallback to client-level default if still None
        if available_slots is None and client_default_slots is not None:
            available_slots = client_default_slots
        
        # Add availability to package dict
        if available_slots is not None:
            pkg_dict["available_slots"] = available_slots
        
        enhanced_items.append(pkg_dict)
    
    return {
        "count": len(enhanced_items),
        "items": enhanced_items
    }
