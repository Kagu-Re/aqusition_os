from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from .api_keys import resolve_tenant_for_public_request, ensure_api_key_or_401
from .console_support import _resolve_db_path
from .public_guard import rate_limit_or_429
from . import repo
from fastapi import Request
from .enums import ChatProvider
from .models import ChatChannel

public_router = APIRouter()


def _find_channel_for_client(
    db_path: str,
    client_id: str,
    provider: Optional[ChatProvider] = None
) -> Optional[ChatChannel]:
    """Find chat channel for a client, with fallback to primary_phone.
    
    Returns a ChatChannel object if found, or None if no channel/phone available.
    For fallback cases, returns a ChatChannel with virtual channel_id for phone-based channels.
    """
    # Get all channels, filter by client_id in meta_json
    channels = repo.list_chat_channels(db_path, provider=None, limit=200)
    
    # Filter by client_id in meta_json
    client_channels = [
        ch for ch in channels 
        if ch.meta_json.get("client_id") == client_id
    ]
    
    # If provider specified, filter further
    if provider:
        client_channels = [ch for ch in client_channels if ch.provider == provider]
    
    if client_channels:
        # Return first matching channel
        return client_channels[0]
    
    # Fallback: check client's primary_phone for phone/WhatsApp
    client = repo.get_client(db_path, client_id)
    if client and client.primary_phone:
        # Return a virtual ChatChannel object for phone-based fallback
        from datetime import datetime
        return ChatChannel(
            channel_id=f"phone_{client_id}",
            provider=ChatProvider.sms,
            handle=client.primary_phone,
            display_name=client.client_name or client_id,
            meta_json={"fallback": True, "client_id": client_id},
            created_at=datetime.utcnow()
        )
    
    return None


@public_router.get("/chat/channel")
def get_chat_channel_for_client(
    client_id: str,
    request: Request,
    provider: Optional[str] = None,
):
    """Get chat channel for a client.
    
    Returns the first available chat channel for the client.
    Used by landing pages to redirect users to chat.
    """
    rate_limit_or_429(request)
    resolve_tenant_for_public_request(request)
    ensure_api_key_or_401(request)
    db_path = _resolve_db_path(request.query_params.get("db"), request)
    
    # Convert provider string to enum if provided
    provider_enum = None
    if provider:
        try:
            provider_enum = ChatProvider(provider.lower())
        except ValueError:
            pass
    
    channel = _find_channel_for_client(db_path, client_id, provider_enum)
    
    if not channel:
        raise HTTPException(status_code=404, detail=f"No chat channel found for client: {client_id}")
    
    # Generate chat URL based on provider
    chat_url = _generate_chat_url(channel.provider.value, channel.handle)
    
    return {
        "channel_id": channel.channel_id,
        "provider": channel.provider.value,
        "handle": channel.handle,
        "display_name": channel.display_name,
        "chat_url": chat_url
    }

def _generate_chat_url(provider: str, handle: str) -> str:
    """Generate chat URL based on provider and handle."""
    provider_lower = provider.lower()
    
    if provider_lower == "whatsapp":
        # WhatsApp: https://wa.me/PHONE or whatsapp://send?phone=PHONE
        phone = handle.replace(" ", "").replace("-", "").replace("+", "")
        return f"https://wa.me/{phone}"
    
    elif provider_lower == "line":
        # LINE: https://line.me/R/ti/p/@LINE_ID or line://
        if handle.startswith("@"):
            return f"https://line.me/R/ti/p/{handle}"
        elif handle.startswith("U"):
            # LINE User ID
            return f"https://line.me/R/ti/p/~{handle}"
        else:
            # Assume it's a LINE ID
            return f"https://line.me/R/ti/p/@{handle}"
    
    elif provider_lower in ["sms", "phone"]:
        # Phone/SMS: tel: protocol
        phone = handle.replace(" ", "").replace("-", "")
        return f"tel:{phone}"
    
    elif provider_lower == "telegram":
        # Telegram: https://t.me/USERNAME
        # Deep links can be added later: https://t.me/USERNAME?start=package_xxx
        username = handle.replace("@", "")
        return f"https://t.me/{username}"
    
    elif provider_lower == "messenger":
        # Facebook Messenger: https://m.me/PAGE_USERNAME
        username = handle.replace("@", "")
        return f"https://m.me/{username}"
    
    else:
        # Fallback: return handle as-is (might be a custom URL)
        return handle
