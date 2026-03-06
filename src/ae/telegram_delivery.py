"""Telegram message delivery helper.

Reuses existing _send_telegram function from repo_alerts.
"""

from __future__ import annotations

from typing import Optional

from .repo_chat_channels import get_chat_channel
from .repo_chat_conversations import get_conversation
from .enums import ChatProvider
from .repo_alerts import _send_telegram  # Reuse existing function


def send_message(db_path: str, conversation_id: str, text: str) -> bool:
    """Send message via Telegram - reuses existing function.
    
    Args:
        db_path: Database path
        conversation_id: Conversation ID
        text: Message text to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    conversation = get_conversation(db_path, conversation_id)
    if not conversation:
        return False
    
    channel = get_chat_channel(db_path, conversation.channel_id)
    if not channel or channel.provider != ChatProvider.telegram:
        return False
    
    # Get bot token from channel config
    bot_token = channel.meta_json.get("telegram_bot_token")
    if not bot_token:
        return False
    
    # Get Telegram chat_id from conversation external_thread_id
    chat_id = conversation.external_thread_id
    if not chat_id:
        return False
    
    # Reuse existing function from repo_alerts
    ok, _ = _send_telegram(bot_token, str(chat_id), text)
    return ok
