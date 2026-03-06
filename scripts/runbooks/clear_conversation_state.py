#!/usr/bin/env python3
"""Clear stale conversation state that might cause multiple /start commands."""

import sys
from src.ae.repo_chat_conversations import list_conversations, get_or_create_conversation

def clear_conversation_state(db_path: str = "acq.db", chat_id: str = None):
    """Clear booking state from conversations."""
    print(f"[ClearState] Clearing conversation state (db: {db_path})\n")
    
    conversations = list_conversations(db_path, limit=100)
    
    cleared_count = 0
    for conv in conversations:
        # Check if conversation has booking state
        has_state = (
            conv.meta_json.get("booking_state") or
            conv.meta_json.get("pending_package_id") or
            conv.meta_json.get("timeslot_list")
        )
        
        # Filter by chat_id if provided
        if chat_id and str(conv.external_thread_id) != str(chat_id):
            continue
        
        if has_state:
            print(f"Clearing state from conversation: {conv.conversation_id}")
            print(f"  External Thread ID: {conv.external_thread_id}")
            print(f"  Old state: booking_state={conv.meta_json.get('booking_state')}, pending_package_id={conv.meta_json.get('pending_package_id')}")
            
            # Clear booking state
            new_meta = conv.meta_json.copy()
            new_meta.pop("booking_state", None)
            new_meta.pop("pending_package_id", None)
            new_meta.pop("timeslot_list", None)
            
            # Update conversation
            get_or_create_conversation(
                db_path,
                conversation_id=conv.conversation_id,
                channel_id=conv.channel_id,
                external_thread_id=conv.external_thread_id,
                meta_json=new_meta
            )
            
            print(f"  [OK] State cleared\n")
            cleared_count += 1
    
    print(f"[ClearState] Cleared state from {cleared_count} conversation(s)")

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "acq.db"
    chat_id = sys.argv[2] if len(sys.argv) > 2 else None
    clear_conversation_state(db_path, chat_id)
