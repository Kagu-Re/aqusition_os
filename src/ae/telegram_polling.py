"""Telegram bot polling (for local development without webhooks).

Uses Telegram Bot API polling instead of webhooks.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

import httpx

from .repo_chat_channels import list_chat_channels, get_chat_channel
from .repo_chat_conversations import get_or_create_conversation, get_conversation, create_conversation_with_message
from .repo_chat_messages import insert_message
from .event_bus import EventBus
from .enums import ChatProvider
from . import repo
from .repo_bookings import get_active_bookings_for_customer, get_customer_by_telegram_id, get_booking
from .service_booking import BookingService
from .repo_payment_intents import list_payment_intents, mark_payment_intent_paid, get_payment_intent
from .repo_leads import get_lead, insert_lead, list_leads, get_or_create_lead_by_telegram_chat_id
from .models import Booking, LeadIntake
from .console_routes_service_packages_public import _calculate_availability_for_package
from .telegram_state import get_state_manager
from .cache import get_cache_manager


# P1 FIX: Centralized logging helper (configurable path, proper error handling)
def _log_debug(data: dict) -> None:
    """Log debug data to file with proper error handling.
    
    Args:
        data: Dictionary to log (will be JSON-serialized)
    """
    log_path = os.getenv("AE_DEBUG_LOG_PATH", r"d:\aqusition_os\.cursor\debug.log")
    try:
        import json as _json
        import time as _time
        data["timestamp"] = int(_time.time() * 1000)
        with open(log_path, "a", encoding="utf-8") as _f:
            _f.write(_json.dumps(data) + "\n")
    except (OSError, IOError, ValueError) as e:
        # Log to stderr if file logging fails (but don't crash)
        safe_print(f"[TelegramPolling] [WARN] Failed to write debug log: {e}")


# Safe print function for Windows console compatibility
def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors on Windows."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Replace emojis with ASCII equivalents for Windows console
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                arg = arg.replace("✅", "[OK]").replace("⚠️", "[WARN]").replace("❌", "[ERROR]").replace("💡", "[INFO]").replace("📝", "[NOTE]")
            safe_args.append(arg)
        print(*safe_args, **kwargs)


class TelegramPollingClient:
    """Telegram bot client using polling (for local development)."""
    
    def __init__(self, bot_token: str, db_path: str, client_id: Optional[str] = None, channel_id: Optional[str] = None):
        self.bot_token = bot_token
        self.db_path = db_path
        self.client_id = client_id
        self.channel_id = channel_id  # Store which channel this bot instance belongs to
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        # Improved timeout configuration: longer timeout for long polling, with retries
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0, read=30.0, write=10.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.last_update_id = 0
        self.running = False
        self.state_manager = get_state_manager()  # Use distributed state manager
        self.instance_id = id(self)  # Unique instance ID for tracking multiple instances
        self._consecutive_network_errors = 0  # Track consecutive network errors for backoff
        self._startup_cleanup_done = False  # Track if startup cleanup has been performed
        self._reset_poll_done = False  # Track if we've done the offset=-1 reset poll
        self._drain_poll_done = False  # Track if we've done the drain poll (if so, skip offset=-1 reset)
    
    async def get_updates(self, timeout: int = 10, *, is_drain_poll: bool = False) -> list[Dict[str, Any]]:
        """Get updates from Telegram.
        
        Args:
            timeout: Long polling timeout in seconds
            is_drain_poll: If True, this is a drain poll (don't use offset=-1 reset)
        """
        # #region agent log
        import json as _json
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","hypothesisId":"D","location":"telegram_polling.py:46","message":"get_updates called","data":{"instance_id":self.instance_id,"last_update_id":self.last_update_id,"timeout":timeout,"is_drain_poll":is_drain_poll},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        try:
            # Use offset = last_update_id + 1 to get only new updates
            # According to Telegram API: offset should be last_update_id + 1
            # CRITICAL FIX: Use offset=-1 ONCE on first poll to reset Telegram's state
            # After that, omit offset when last_update_id==0 to get all unconfirmed updates
            # Using offset=-1 repeatedly clears updates as they arrive, preventing message delivery
            # NEVER use offset=-1 in drain polls - it will clear updates that arrive during the poll
            params = {
                "timeout": timeout,
                "allowed_updates": ["message", "callback_query"]
            }
            if self.last_update_id > 0:
                # Use offset = last_update_id + 1 for subsequent polls
                params["offset"] = self.last_update_id + 1
            elif not self._reset_poll_done and not is_drain_poll:
                # First main poll (NOT drain poll): Use offset=-1 ONCE to reset Telegram's update state
                # This clears any stale offset state from previous runs
                # CRITICAL: We use offset=-1 on the FIRST main poll, regardless of drain_poll_done status
                # The drain poll already consumed old updates, so offset=-1 here just resets Telegram's internal state
                params["offset"] = -1
                self._reset_poll_done = True  # Mark that we've done the reset poll
            # else: omit offset entirely - Telegram will return all unconfirmed updates
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H12","location":"telegram_polling.py:110","message":"get_updates request params","data":{"instance_id":self.instance_id,"offset":params.get("offset"),"last_update_id":self.last_update_id,"timeout":timeout},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            response = await self.client.get(
                f"{self.api_url}/getUpdates",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            # #region agent log
            try:
                # Log full response for debugging (but limit result size)
                result = data.get("result", [])
                result_preview = []
                for update in result[:3]:  # Only log first 3 updates
                    update_preview = {"update_id": update.get("update_id")}
                    if "message" in update:
                        msg = update["message"]
                        update_preview["message"] = {
                            "chat_id": msg.get("chat", {}).get("id"),
                            "message_id": msg.get("message_id"),
                            "text_preview": str(msg.get("text", ""))[:50]
                        }
                    result_preview.append(update_preview)
                
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H12","location":"telegram_polling.py:139","message":"get_updates API response","data":{"instance_id":self.instance_id,"ok":data.get("ok"),"error_code":data.get("error_code"),"description":data.get("description"),"result_count":len(result),"result_preview":result_preview,"offset_used":params.get("offset")},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as log_err:
                safe_print(f"[TelegramPolling] [WARN] Failed to log API response: {log_err}")
            # #endregion
            if data.get("ok"):
                updates = data.get("result", [])
                # Reset consecutive error counter on successful API response
                self._consecutive_network_errors = 0
                
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H12","location":"telegram_polling.py:151","message":"updates received from Telegram API","data":{"instance_id":self.instance_id,"update_count":len(updates),"update_ids":[u.get("update_id") for u in updates],"last_update_id_before":self.last_update_id,"offset_used":params.get("offset")},"timestamp":int(time.time()*1000)})+"\n")
                except Exception as e:
                    safe_print(f"[TelegramPolling] [WARN] Failed to log updates received: {e}")
                # #endregion
                # P0 FIX: Don't advance offset here - will be advanced after successful processing
                # This prevents message loss if processing fails
                return updates
            else:
                # Handle Telegram API errors - CRITICAL: Don't silently fail!
                error_code = data.get("error_code")
                description = data.get("description", "Unknown error")
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"D","location":"telegram_polling.py:115","message":"get_updates API error response","data":{"instance_id":self.instance_id,"error_code":error_code,"description":description},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                
                # Handle specific error codes
                if error_code == 429:
                    # Rate limited - wait longer before retrying
                    retry_after = data.get("parameters", {}).get("retry_after", 60)
                    safe_print(f"[TelegramPolling] [WARN] Rate limited by Telegram API. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                elif error_code == 401:
                    # Unauthorized - invalid token
                    safe_print(f"[TelegramPolling] [ERROR] Invalid bot token! Error: {description}")
                    safe_print(f"[TelegramPolling] [ERROR] Bot token prefix: {self.bot_token[:20]}...")
                    # Don't stop polling immediately, but log the error
                elif error_code == 409:
                    # Conflict - webhook conflict (polling and webhook can't coexist)
                    safe_print(f"[TelegramPolling] [WARN] Webhook conflict detected. Attempting to delete webhook...")
                    try:
                        delete_response = await self.client.get(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": True})
                        delete_data = delete_response.json()
                        if delete_data.get("ok"):
                            safe_print(f"[TelegramPolling] [OK] Webhook deleted successfully")
                        else:
                            safe_print(f"[TelegramPolling] [WARN] Failed to delete webhook: {delete_data.get('description')}")
                    except Exception as e:
                        safe_print(f"[TelegramPolling] [WARN] Error deleting webhook: {e}")
                else:
                    # Other API errors
                    safe_print(f"[TelegramPolling] [WARN] Telegram API error (code {error_code}): {description}")
                
                return []
        except (httpx.ReadError, httpx.ConnectError, httpx.NetworkError, httpx.TimeoutException) as e:
            # Network-level errors (transient) - retry with backoff
            self._consecutive_network_errors += 1
            error_type = type(e).__name__
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"D","location":"telegram_polling.py:168","message":"get_updates network error","data":{"instance_id":self.instance_id,"error":str(e),"error_type":error_type,"consecutive_errors":self._consecutive_network_errors},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as log_err:
                safe_print(f"[TelegramPolling] [WARN] Failed to log network error: {log_err}")
            # #endregion
            
            # Exponential backoff: 5s, 10s, 20s, max 60s
            backoff_seconds = min(5 * (2 ** (self._consecutive_network_errors - 1)), 60)
            safe_print(f"[TelegramPolling] [WARN] Network error ({error_type}): {e}")
            safe_print(f"[TelegramPolling] [INFO] Retrying in {backoff_seconds}s (consecutive errors: {self._consecutive_network_errors})")
            
            await asyncio.sleep(backoff_seconds)
            return []
        except httpx.HTTPStatusError as e:
            # HTTP status errors (4xx, 5xx) - log and retry
            self._consecutive_network_errors += 1
            status_code = e.response.status_code
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H9","location":"telegram_polling.py:197","message":"get_updates HTTP error","data":{"instance_id":self.instance_id,"status_code":status_code,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as log_err:
                safe_print(f"[TelegramPolling] [WARN] Failed to log HTTP error: {log_err}")
            # #endregion
            
            # CRITICAL: Handle 409 Conflict (webhook active) aggressively
            if status_code == 409:
                safe_print(f"[TelegramPolling] [ERROR] 409 Conflict - webhook is active, blocking polling!")
                safe_print(f"[TelegramPolling] [INFO] Attempting to delete webhook immediately...")
                try:
                    # Try to get webhook info first
                    webhook_check = await self.client.get(f"{self.api_url}/getWebhookInfo")
                    webhook_data = webhook_check.json()
                    if webhook_data.get("ok"):
                        webhook_info = webhook_data.get("result", {})
                        webhook_url = webhook_info.get("url", "")
                        pending_count = webhook_info.get("pending_update_count", 0)
                        safe_print(f"[TelegramPolling] [WARN] Active webhook found: {webhook_url} (pending: {pending_count})")
                    
                    # Delete webhook aggressively
                    delete_response = await self.client.get(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": False})
                    delete_data = delete_response.json()
                    if delete_data.get("ok"):
                        safe_print(f"[TelegramPolling] [OK] Webhook deleted successfully - retrying getUpdates...")
                        # Wait a moment for Telegram to process
                        await asyncio.sleep(1)
                        # CRITICAL: Retry getUpdates immediately after deleting webhook
                        # Use offset=0 to get all available updates
                        try:
                            retry_response = await self.client.get(
                                f"{self.api_url}/getUpdates",
                                params={
                                    "offset": 0,
                                    "timeout": min(timeout, 5),  # Use shorter timeout for retry
                                    "allowed_updates": ["message", "callback_query"]
                                }
                            )
                            retry_response.raise_for_status()
                            retry_data = retry_response.json()
                            if retry_data.get("ok"):
                                updates = retry_data.get("result", [])
                                safe_print(f"[TelegramPolling] [OK] Retry successful - received {len(updates)} update(s)")
                                # Reset error counter on successful retry
                                self._consecutive_network_errors = 0
                                # #region agent log
                                try:
                                    import json as _json
                                    import time as _time
                                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H9","location":"telegram_polling.py:268","message":"409 retry successful","data":{"instance_id":self.instance_id,"update_count":len(updates),"update_ids":[u.get("update_id") for u in updates[:5]]},"timestamp":int(_time.time()*1000)})+"\n")
                                except Exception as log_err:
                                    pass
                                # #endregion
                                return updates
                            else:
                                safe_print(f"[TelegramPolling] [WARN] Retry still failed: {retry_data.get('description')}")
                        except Exception as retry_err:
                            safe_print(f"[TelegramPolling] [WARN] Retry failed: {retry_err}")
                    else:
                        safe_print(f"[TelegramPolling] [ERROR] Failed to delete webhook: {delete_data.get('description')}")
                        safe_print(f"[TelegramPolling] [ERROR] Please delete webhook manually via BotFather or API")
                except Exception as del_err:
                    safe_print(f"[TelegramPolling] [ERROR] Error deleting webhook: {del_err}")
                    import traceback
                    safe_print(f"[TelegramPolling] [ERROR] Traceback: {traceback.format_exc()}")
            
            safe_print(f"[TelegramPolling] [ERROR] HTTP error {status_code}: {e}")
            await asyncio.sleep(5)
            return []
        except Exception as e:
            # Other unexpected errors
            self._consecutive_network_errors += 1
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"D","location":"telegram_polling.py:190","message":"get_updates unexpected error","data":{"instance_id":self.instance_id,"error":str(e),"error_type":type(e).__name__},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as log_err:
                safe_print(f"[TelegramPolling] [WARN] Failed to log error: {log_err}")
            # #endregion
            safe_print(f"[TelegramPolling] [ERROR] Unexpected error getting updates: {e}")
            import traceback
            safe_print(f"[TelegramPolling] [ERROR] Traceback: {traceback.format_exc()}")
            await asyncio.sleep(5)
            return []
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a message via Telegram."""
        # #region agent log
        import json as _json
        import time as _time
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"debug","hypothesisId":"H4","location":"telegram_polling.py:226","message":"send_message called","data":{"instance_id":self.instance_id,"chat_id":chat_id,"text_length":len(text),"text_preview":text[:100]},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            response = await self.client.post(
                f"{self.api_url}/sendMessage",
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H4","location":"telegram_polling.py:255","message":"send_message API response","data":{"instance_id":self.instance_id,"chat_id":chat_id,"ok":response_data.get("ok"),"message_id":response_data.get("result",{}).get("message_id"),"error_code":response_data.get("error_code"),"description":response_data.get("description")},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            if not response_data.get("ok"):
                safe_print(f"[TelegramPolling] [ERROR] Failed to send message: {response_data.get('description')}")
                return False
            return True
        except Exception as e:
            # #region agent log
            try:
                import traceback as _tb
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H4","location":"telegram_polling.py:266","message":"send_message exception","data":{"instance_id":self.instance_id,"chat_id":chat_id,"error":str(e),"error_type":type(e).__name__,"traceback":_tb.format_exc()},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [ERROR] Error sending message: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming Telegram message."""
        chat_id = str(message["chat"]["id"])
        text = message.get("text", "")
        message_id = str(message["message_id"])
        update_id = message.get("update_id")  # Get update_id if available
        
        # #region agent log
        try:
            import json as _json
            import time as _time
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:377","message":"handle_message entry","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"update_id":update_id,"text_preview":text[:50],"db_path":self.db_path},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # #region agent log
        import json as _json
        try:
            # P1 FIX: Use state_manager instead of undefined self.processed_message_ids
            is_already_processed = await self.state_manager.is_message_processed(f"{chat_id}:{message_id}")
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","hypothesisId":"D","location":"telegram_polling.py:93","message":"handle_message called","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"update_id":update_id,"text":text[:50],"message_key":f"{chat_id}:{message_id}","already_processed":is_already_processed},"timestamp":int(time.time()*1000)})+"\n")
        except Exception as e:
            safe_print(f"[TelegramPolling] [WARN] Failed to log handle_message call: {e}")
        # #endregion
        
        # Deduplicate: Skip if we've already processed this message
        message_key = f"{chat_id}:{message_id}"
        is_processed = await self.state_manager.is_message_processed(message_key)
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"debug","hypothesisId":"H5","location":"telegram_polling.py:298","message":"checking message deduplication","data":{"instance_id":self.instance_id,"message_key":message_key,"is_processed":is_processed},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        if is_processed:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H5","location":"telegram_polling.py:305","message":"duplicate message detected and skipped","data":{"instance_id":self.instance_id,"message_key":message_key},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            return
        await self.state_manager.mark_message_processed(message_key)
        
        # Early cooldown check for /start commands to prevent rapid duplicates
        text_lower = text.strip().lower()
        from_user = message.get("from", {})
        username = from_user.get("username")
        
        # Find Telegram channel (with caching)
        try:
            cache_mgr = get_cache_manager()
            cache_key = f"channels:telegram:{self.client_id or 'all'}"
            channels = await cache_mgr.get(cache_key)
            if channels is None:
                channels = list_chat_channels(self.db_path, provider=ChatProvider.telegram, limit=10)
                await cache_mgr.set(cache_key, channels, ttl_seconds=300)  # Cache for 5 minutes
        except Exception as channel_error:
            # #region agent log
            try:
                import json as _json
                import time as _time
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:424","message":"list_chat_channels failed","data":{"instance_id":self.instance_id,"chat_id":chat_id,"error":str(channel_error),"error_type":type(channel_error).__name__},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [ERROR] Error listing chat channels: {channel_error}")
            import traceback
            safe_print(f"[TelegramPolling] [ERROR] Channel lookup traceback: {traceback.format_exc()}")
            # Send error message and return - can't proceed without channels
            try:
                await self.send_message(chat_id, "Sorry, there was an error processing your message. Please try again.")
            except Exception as send_error:
                safe_print(f"[TelegramPolling] [ERROR] Failed to send error message: {send_error}")
            return
        if not channels:
            # P1 FIX: Send error response instead of silent failure
            safe_print(f"[TelegramPolling] [ERROR] No Telegram channels configured for chat_id: {chat_id}")
            try:
                await self.send_message(chat_id, "Sorry, the bot is not properly configured. Please contact support.")
            except Exception as e:
                safe_print(f"[TelegramPolling] [ERROR] Failed to send error message: {e}")
            return
        
        # Use stored channel_id if available (for vendor/customer bot distinction)
        channel = None
        if self.channel_id:
            for ch in channels:
                if ch.channel_id == self.channel_id:
                    channel = ch
                    break
        
        # Filter by client_id if specified
        if not channel and self.client_id:
            for ch in channels:
                if ch.meta_json.get("client_id") == self.client_id:
                    channel = ch
                    break
        
        if not channel:
            # Prefer customer bot channels (non-vendor) when client_id not specified
            for ch in channels:
                if ch.meta_json.get("bot_type") != "vendor":
                    channel = ch
                    break
            # Fallback to first channel if no customer bot found
            if not channel:
                channel = channels[0]
        
        # Get or create conversation and insert message atomically
        conversation_id = f"conv_telegram_{chat_id}"
        # First, try to get existing conversation to preserve meta_json
        try:
            existing_conversation = get_conversation(self.db_path, conversation_id)
        except Exception as get_conv_error:
            # #region agent log
            try:
                import json as _json
                import time as _time
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:463","message":"get_conversation failed","data":{"instance_id":self.instance_id,"chat_id":chat_id,"conversation_id":conversation_id,"error":str(get_conv_error),"error_type":type(get_conv_error).__name__},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [WARN] Error getting existing conversation (non-blocking): {get_conv_error}")
            existing_conversation = None
        
        # Merge new meta with existing meta to preserve state like pending_package_id
        base_meta = existing_conversation.meta_json.copy() if existing_conversation else {}
        new_meta = {
            "telegram_chat_id": chat_id,
            "telegram_username": username,
        }
        # Merge: new values override, but preserve existing keys
        merged_meta = {**base_meta, **new_meta}
        
        # Use transaction-aware function to create conversation and message atomically
        try:
            conversation, _ = create_conversation_with_message(
                self.db_path,
                conversation_id=conversation_id,
                channel_id=channel.channel_id,
                external_thread_id=str(chat_id),
                meta_json=merged_meta,
                message_text=text,
                message_external_msg_id=message_id,
                message_payload_json={"telegram_message": message},
                message_ts=datetime.utcnow()
            )
        except Exception as db_error:
            # P1 FIX: Log database errors but still try to respond to user
            safe_print(f"[TelegramPolling] [ERROR] Database error creating conversation/message: {db_error}")
            import traceback
            safe_print(f"[TelegramPolling] [ERROR] Database error traceback: {traceback.format_exc()}")
            # #region agent log
            try:
                import json as _json
                import time as _time
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:475","message":"create_conversation_with_message failed","data":{"instance_id":self.instance_id,"chat_id":chat_id,"conversation_id":conversation_id,"error":str(db_error),"error_type":type(db_error).__name__},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            # Try to get existing conversation as fallback
            try:
                conversation = get_conversation(self.db_path, conversation_id)
                if not conversation:
                    # Can't proceed without conversation - send error and return
                    await self.send_message(chat_id, "Sorry, there was an error processing your message. Please try again.")
                    return
            except Exception as fallback_error:
                safe_print(f"[TelegramPolling] [ERROR] Fallback conversation lookup also failed: {fallback_error}")
                await self.send_message(chat_id, "Sorry, there was an error processing your message. Please try again.")
                return
        
        # Emit event (best-effort - don't block message processing)
        try:
            EventBus.emit_topic(
                self.db_path,
                topic="op.chat.message_received",
                aggregate_type="chat",
                aggregate_id=conversation.conversation_id,
                payload={
                    "conversation_id": conversation.conversation_id,
                    "text": text,
                    "channel": "telegram",
                    "chat_id": chat_id
                },
                correlation_id=None,
            )
        except Exception as event_error:
            # P1 FIX: Log event bus errors but don't block message processing
            # Event bus failures shouldn't prevent bot from responding
            safe_print(f"[TelegramPolling] [WARN] EventBus.emit_topic failed (non-blocking): {event_error}")
            import traceback
            safe_print(f"[TelegramPolling] [WARN] EventBus error traceback: {traceback.format_exc()}")
            # #region agent log
            try:
                import json as _json
                import time as _time
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:500","message":"EventBus.emit_topic failed","data":{"instance_id":self.instance_id,"chat_id":chat_id,"conversation_id":conversation.conversation_id,"error":str(event_error),"error_type":type(event_error).__name__},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
        
        # #region agent log
        try:
            import json as _json
            import time as _time
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"debug","hypothesisId":"H13","location":"telegram_polling.py:520","message":"after EventBus.emit_topic","data":{"instance_id":self.instance_id,"chat_id":chat_id,"conversation_id":conversation.conversation_id if conversation else None},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # Check if this is a vendor bot
        is_vendor_bot = channel.meta_json.get("bot_type") == "vendor"
        
        if is_vendor_bot:
            # Handle vendor bot commands (with authorization check)
            await self.handle_vendor_command(chat_id, text, channel)
        else:
            # Handle customer bot commands
            text_lower = text.strip().lower()
            
            # Check conversation state FIRST to handle context-aware responses
            booking_state = conversation.meta_json.get("booking_state")
            
            if text_lower.startswith("/start"):
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:244","message":"/start command detected in customer bot handler","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"text":text[:50]},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                # CRITICAL: Check lock FIRST to prevent concurrent processing
                # This ensures that even if user has multiple bookings, /start is only processed once
                current_time = time.time()
                lock_acquired = await self.state_manager.try_acquire_start_lock(chat_id)
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H6","location":"telegram_polling.py:419","message":"/start lock check","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"lock_acquired":lock_acquired},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                if not lock_acquired:
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"debug","hypothesisId":"H6","location":"telegram_polling.py:426","message":"/start blocked - already processing (early check)","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    safe_print(f"[TelegramPolling] [WARN] /start blocked - already processing for chat_id {chat_id} (message_id: {message_id})")
                    return
                
                last_start_time = await self.state_manager.get_start_cooldown(chat_id)
                time_since_last = current_time - last_start_time
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"E","location":"telegram_polling.py:290","message":"/start command detected","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"update_id":update_id,"text":text,"time_since_last":time_since_last,"last_start_time":last_start_time},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                
                if time_since_last < 3.0:  # Increased to 3 seconds
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"E","location":"telegram_polling.py:300","message":"/start blocked by cooldown","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"time_since_last":time_since_last},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    safe_print(f"[TelegramPolling] [WARN] Ignoring duplicate /start command from chat_id {chat_id} (last: {time_since_last:.2f}s ago, message_id: {message_id})")
                    return
                
                # Lock already acquired above, just update cooldown
                await self.state_manager.set_start_cooldown(chat_id, current_time)
                
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"J","location":"telegram_polling.py:310","message":"/start lock acquired","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                
                # Extract deep link parameter if present
                args = text.split()[1:] if len(text.split()) > 1 else []
                deep_link_param = None
                if args:
                    if args[0].startswith("package_"):
                        deep_link_param = args[0]
                    elif args[0] == "intent_contact":
                        deep_link_param = "intent_contact"
                
                # Lock is already set, process the command
                try:
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:297","message":"/start try block entered","data":{"instance_id":self.instance_id,"chat_id":chat_id,"deep_link_param":deep_link_param},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    # Check if we've already processed this exact deep link recently (within 5 seconds)
                    if deep_link_param:
                        deep_link_key = f"{chat_id}:{deep_link_param}"
                        last_processed_time = await self.state_manager.get_deep_link_time(deep_link_key)
                        if current_time - last_processed_time < 5.0:
                            # #region agent log
                            try:
                                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                    _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"E","location":"telegram_polling.py:280","message":"/start blocked - duplicate deep link","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"deep_link_param":deep_link_param,"time_since_last":current_time-last_processed_time},"timestamp":int(time.time()*1000)})+"\n")
                            except: pass
                            # #endregion
                            safe_print(f"[TelegramPolling] [WARN] Duplicate deep link blocked: {deep_link_param} from chat_id {chat_id} (processed {current_time - last_processed_time:.2f}s ago)")
                            return
                        # Mark this deep link as processed
                        await self.state_manager.set_deep_link_time(deep_link_key, current_time)
                    
                    if deep_link_param and deep_link_param.startswith("package_"):
                        # Package deep link: cancel existing bookings and show package
                        customer = get_customer_by_telegram_id(self.db_path, chat_id)
                        cancelled_bookings = []
                        if customer:
                            active_bookings = get_active_bookings_for_customer(self.db_path, customer.customer_id)
                            svc = BookingService(self.db_path)
                            if active_bookings:
                                for booking in active_bookings:
                                    try:
                                        svc.cancel_booking(booking.booking_id, actor_id="telegram_bot", reason="replaced_by_new_booking")
                                        cancelled_bookings.append(booking.booking_id)
                                        # #region agent log
                                        try:
                                            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                                _f.write(_json.dumps({"runId":"run1","hypothesisId":"I","location":"telegram_polling.py:318","message":"cancelled existing booking for new booking","data":{"instance_id":self.instance_id,"chat_id":chat_id,"cancelled_booking_id":booking.booking_id},"timestamp":int(time.time()*1000)})+"\n")
                                        except: pass
                                        # #endregion
                                    except Exception as e:
                                        safe_print(f"[TelegramPolling] [WARN] Error cancelling booking {booking.booking_id}: {e}")
                                if cancelled_bookings:
                                    # #region agent log
                                    try:
                                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"I","location":"telegram_polling.py:337","message":"sending booking replacement notification","data":{"instance_id":self.instance_id,"chat_id":chat_id,"cancelled_count":len(cancelled_bookings)},"timestamp":int(time.time()*1000)})+"\n")
                                    except: pass
                                    # #endregion
                                    await self.send_message(
                                        conversation.external_thread_id,
                                        f"🔄 Replacing your existing booking{'s' if len(cancelled_bookings) > 1 else ''} with a new one..."
                                    )
                        conversation_meta = conversation.meta_json.copy()
                        conversation_meta.pop("pending_package_id", None)
                        conversation_meta.pop("booking_state", None)
                        conversation_meta.pop("timeslot_list", None)
                        get_or_create_conversation(
                            self.db_path,
                            conversation_id=conversation.conversation_id,
                            channel_id=conversation.channel_id,
                            external_thread_id=conversation.external_thread_id,
                            meta_json=conversation_meta
                        )
                        # #region agent log
                        try:
                            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                _f.write(_json.dumps({"runId":"run1","hypothesisId":"I","location":"telegram_polling.py:360","message":"/start command processing after cancelling old bookings","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"deep_link_param":deep_link_param,"cancelled_count":len(cancelled_bookings)},"timestamp":int(time.time()*1000)})+"\n")
                        except: pass
                        # #endregion
                        package_id = deep_link_param.replace("package_", "")
                        await self.handle_package_deep_link(conversation, channel, package_id)
                    elif deep_link_param == "intent_contact":
                        # Contact Us deep link: show contact-specific welcome (no booking cancellation)
                        await self.handle_contact_intent(conversation, channel)
                    else:
                        # Plain /start command - show welcome message
                        # #region agent log
                        try:
                            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:400","message":"calling handle_start_command","data":{"instance_id":self.instance_id,"chat_id":chat_id},"timestamp":int(time.time()*1000)})+"\n")
                        except: pass
                        # #endregion
                        await self.handle_start_command(conversation, channel)
                except Exception as e:
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:400","message":"/start exception caught","data":{"instance_id":self.instance_id,"chat_id":chat_id,"error":str(e),"error_type":type(e).__name__},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    safe_print(f"[TelegramPolling] [ERROR] Error processing /start command: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # Always release lock, even if an error occurred
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:410","message":"/start finally block - releasing lock","data":{"instance_id":self.instance_id,"chat_id":chat_id},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    await self.state_manager.release_start_lock(chat_id)
            elif text_lower in ["yes", "y"]:
                # Handle package confirmation (check before contact mode - user may have selected package from contact flow)
                await self.handle_package_confirmation(conversation, channel)
            elif text_lower in ["no", "n"]:
                # Handle package rejection - show available packages
                await self.handle_package_selection(conversation, channel)
            elif booking_state == "awaiting_time_window":
                # User is in timeslot selection flow - prioritize this over package selection
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","location":"telegram_polling.py:343","message":"triggering timeslot selection from handle_message","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"text":text,"booking_state":booking_state,"pending_package_id":conversation.meta_json.get("pending_package_id")},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                await self.handle_timeslot_selection(conversation, channel, text_lower)
            elif text_lower.isdigit() and 1 <= int(text_lower) <= 10:
                # Handle package number selection (only if not in timeslot flow)
                await self.handle_package_number_selection(conversation, channel, int(text_lower))
            elif text_lower in ["morning", "afternoon", "evening"]:
                # Handle timeslot selection (text keywords)
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","location":"telegram_polling.py:351","message":"triggering timeslot selection (keyword)","data":{"instance_id":self.instance_id,"chat_id":chat_id,"message_id":message_id,"text":text,"pending_package_id":conversation.meta_json.get("pending_package_id")},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                await self.handle_timeslot_selection(conversation, channel, text_lower)
            elif conversation.meta_json.get("conversation_mode") == "contact":
                await self._handle_contact_mode_message(conversation, channel, text_lower)
            else:
                # For other messages, provide helpful response
                await self.send_message(
                    conversation.external_thread_id,
                    "I'm here to help you book a massage service. Send /start to begin, or visit our website to select a package."
                )
    
    async def handle_package_deep_link(
        self,
        conversation: Any,
        channel: Any,
        package_id: str
    ) -> None:
        """Handle package deep link from landing page."""
        # #region agent log
        import json as _json
        import time as _time
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:432","message":"handle_package_deep_link entry","data":{"instance_id":self.instance_id,"chat_id":conversation.external_thread_id,"package_id":package_id},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # Get package info (with caching)
        cache_mgr = get_cache_manager()
        cache_key = f"package:{package_id}"
        package = await cache_mgr.get(cache_key)
        if package is None:
            package = repo.get_package(self.db_path, package_id)
            if package:
                await cache_mgr.set(cache_key, package, ttl_seconds=300)  # Cache for 5 minutes
        if not package:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, the selected package is no longer available. Please visit our website to see current packages."
            )
            return
        
        # Store package_id in conversation meta
        conversation_meta = conversation.meta_json.copy()
        conversation_meta["pending_package_id"] = package_id
        
        # Update conversation
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
        
        # Send package confirmation message
        message = f"""✅ Package Selected!

📦 {package.name}
💰 ฿{package.price:.0f}
⏱️ {package.duration_min} minutes

Confirm this package?
Reply with "yes" to continue or "no" to choose a different package."""
        
        await self.send_message(conversation.external_thread_id, message)
    
    async def handle_start_command(
        self,
        conversation: Any,
        channel: Any
    ) -> None:
        """Handle plain /start command - show welcome message."""
        client_id = channel.meta_json.get("client_id")
        client = None
        if client_id:
            client = repo.get_client(self.db_path, client_id)
        
        # Build welcome message
        client_name = getattr(client, "name", "our service") if client else "our service"
        welcome = f"""👋 Welcome to {client_name}!

I'm here to help you book a massage service. 

"""
        
        welcome += "To get started, please visit our website and select a package. When you click on a package, you'll be redirected here with all the details pre-filled.\n\n"
        
        welcome += "💬 You can also ask me questions about our services, pricing, or availability."
        
        await self.send_message(conversation.external_thread_id, welcome)
    
    async def handle_contact_intent(
        self,
        conversation: Any,
        channel: Any
    ) -> None:
        """Handle Contact Us flow - user wants info or has a question."""
        client_id = channel.meta_json.get("client_id")
        client = None
        if client_id:
            client = repo.get_client(self.db_path, client_id)
        client_name = getattr(client, "client_name", None) or getattr(client, "name", "our service") if client else "our service"
        
        welcome = f"""👋 Hi! You've reached {client_name}. I'm here to help.

What would you like to do?
1. Ask a question (hours, location, services)
2. See our packages and book
3. Type your question

Reply with a number or type your question directly."""
        
        await self.send_message(conversation.external_thread_id, welcome)
        
        # Store conversation mode for follow-up message routing
        conversation_meta = conversation.meta_json.copy()
        conversation_meta["conversation_mode"] = "contact"
        conversation_meta.pop("pending_package_id", None)
        conversation_meta.pop("booking_state", None)
        conversation_meta.pop("timeslot_list", None)
        conversation_meta.pop("package_list", None)
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
    
    def _get_contact_faq_response(self, client: Any, keyword: str) -> Optional[str]:
        """Build FAQ response from client data for contact mode keywords."""
        if not client:
            return None
        kw = keyword.lower()
        if kw in ("hours", "open", "when"):
            hours = getattr(client, "hours", None)
            if not hours:
                try:
                    from .trade_templates import get_trade_template_or_fallback
                    from .enums import Trade
                    trade = getattr(client, "trade", None)
                    if trade is not None:
                        tpl = get_trade_template_or_fallback(Trade(trade) if isinstance(trade, str) else trade)
                        hours = tpl.default_hours if tpl else None
                except (ValueError, TypeError):
                    hours = None
            if hours:
                return f"We're open {hours}."
            return None
        if kw in ("location", "where", "address"):
            area = getattr(client, "service_area", None)
            city = getattr(client, "geo_city", None)
            if area and len(area) > 0:
                return f"We serve {area[0]} and surrounding areas."
            if city:
                return f"We're based in {city}."
            return None
        if kw in ("phone", "call"):
            phone = getattr(client, "primary_phone", None)
            if phone:
                return f"You can reach us at {phone}."
            return None
        return None
    
    async def _handle_contact_mode_message(
        self, conversation: Any, channel: Any, text_lower: str
    ) -> None:
        """Handle follow-up messages when in contact mode."""
        client_id = channel.meta_json.get("client_id")
        client = repo.get_client(self.db_path, client_id) if client_id else None
        
        package_list = conversation.meta_json.get("package_list", [])
        
        # Menu choice: 1=packages, 2=question hint, 3=type hint
        if text_lower.isdigit() and 1 <= int(text_lower) <= 10:
            if package_list:
                await self.handle_package_number_selection(conversation, channel, int(text_lower))
                return
            choice = int(text_lower)
            if choice == 1:
                await self.handle_package_selection(conversation, channel)
                return
            if choice == 2:
                await self.send_message(
                    conversation.external_thread_id,
                    "Type your question and I'll do my best to help, or share it with our team."
                )
                return
            if choice == 3:
                await self.send_message(
                    conversation.external_thread_id,
                    "Go ahead and type your question. I can also answer quick questions about hours, location, or packages."
                )
                return
        
        # Keyword matches for quick FAQ
        if text_lower in ("hours", "open", "when"):
            resp = self._get_contact_faq_response(client, "hours")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
            else:
                await self.send_message(conversation.external_thread_id, "I don't have hours info at the moment. Please visit our website or send a message and we'll get back to you.")
            return
        if text_lower in ("location", "where", "address"):
            resp = self._get_contact_faq_response(client, "location")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
            else:
                await self.send_message(conversation.external_thread_id, "I don't have location details at the moment. Please send a message and we'll get back to you.")
            return
        if text_lower in ("phone", "call"):
            resp = self._get_contact_faq_response(client, "phone")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
            else:
                await self.send_message(conversation.external_thread_id, "I don't have contact details at the moment. Please visit our website.")
            return
        if text_lower in ("packages", "book"):
            await self.handle_package_selection(conversation, channel)
            return
        
        # Partial keyword match (e.g. "what are your hours?")
        if any(w in text_lower for w in ("hours", "open", "when")):
            resp = self._get_contact_faq_response(client, "hours")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
                return
        if any(w in text_lower for w in ("location", "where", "address")):
            resp = self._get_contact_faq_response(client, "location")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
                return
        if any(w in text_lower for w in ("phone", "call", "contact")):
            resp = self._get_contact_faq_response(client, "phone")
            if resp:
                await self.send_message(conversation.external_thread_id, resp)
                return
        if any(w in text_lower for w in ("packages", "book", "pricing")):
            await self.handle_package_selection(conversation, channel)
            return
        
        # Unmatched free text - fallback
        fallback = (
            "I'll share your message with our team. "
            "You can also type 'packages' to see our services, or 'hours'/'location' for quick info."
        )
        await self.send_message(conversation.external_thread_id, fallback)
    
    async def handle_package_confirmation(
        self,
        conversation: Any,
        channel: Any
    ) -> None:
        """Handle package confirmation (user replied 'yes')."""
        package_id = conversation.meta_json.get("pending_package_id")
        if not package_id:
            await self.send_message(
                conversation.external_thread_id,
                "I don't see a pending package. Please visit our website and select a package to get started."
            )
            return
        
        # Get package (with caching)
        cache_mgr = get_cache_manager()
        cache_key = f"package:{package_id}"
        package = await cache_mgr.get(cache_key)
        if package is None:
            package = repo.get_package(self.db_path, package_id)
            if package:
                await cache_mgr.set(cache_key, package, ttl_seconds=300)
        if not package:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, the selected package is no longer available. Please visit our website to see current packages."
            )
            return
        
        # Get client for currency symbol
        client_id = channel.meta_json.get("client_id")
        currency_symbol = "฿"  # Default
        if client_id:
            client = repo.get_client(self.db_path, client_id)
            if client:
                geo_country = getattr(client, "geo_country", "").upper()
                if geo_country == "AU":
                    currency_symbol = "A$"
                elif geo_country == "US":
                    currency_symbol = "$"
                elif geo_country in ["TH", "THA"]:
                    currency_symbol = "฿"
        
        # Calculate availability for each timeslot
        timeslots = [
            {"name": "Morning (9am-12pm)", "key": "morning", "normalized": "Morning (9am-12pm)"},
            {"name": "Afternoon (12pm-5pm)", "key": "afternoon", "normalized": "Afternoon (12pm-5pm)"},
            {"name": "Evening (5pm-9pm)", "key": "evening", "normalized": "Evening (5pm-9pm)"},
        ]
        
        timeslot_list = []
        for idx, slot in enumerate(timeslots, 1):
            # Calculate availability for this timeslot
            # For now, we'll use the package's overall availability
            # In the future, this could be timeslot-specific
            availability = _calculate_availability_for_package(
                self.db_path,
                package_id,
                package.meta_json or {}
            )
            
            if availability is None:
                availability_text = "Available"
            elif availability == 0:
                availability_text = "Fully booked"
            else:
                availability_text = f"{availability} slot{'s' if availability != 1 else ''} available"
            
            timeslot_list.append({
                "number": idx,
                "name": slot["name"],
                "key": slot["key"],
                "normalized": slot["normalized"],
                "availability": availability
            })
        
        # Build message with availability
        message = f"""✅ Great! You've confirmed:

📦 {package.name}
💰 {currency_symbol}{package.price:.0f}
⏱️ {package.duration_min} minutes

⏰ When would you prefer your appointment?

Please reply with your preferred time window:
"""
        for slot in timeslot_list:
            if slot["availability"] == 0:
                message += f"• {slot['number']}. {slot['name']} - Fully booked\n"
            else:
                avail_text = f"{slot['availability']} slot{'s' if slot['availability'] != 1 else ''} available" if slot["availability"] is not None else "Available"
                message += f"• {slot['number']}. {slot['name']} - {avail_text}\n"
        
        message += "\nOr reply with the number (1, 2, 3) or the time window name."
        
        await self.send_message(conversation.external_thread_id, message)
        
        # Store timeslot list in conversation meta
        conversation_meta = conversation.meta_json.copy()
        conversation_meta["booking_state"] = "awaiting_time_window"
        conversation_meta["timeslot_list"] = timeslot_list
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
    
    async def handle_package_selection(
        self,
        conversation: Any,
        channel: Any
    ) -> None:
        """Handle package selection (user said 'no' to pre-filled package)."""
        client_id = channel.meta_json.get("client_id")
        if not client_id:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, I couldn't find the client information. Please visit our website to see available packages."
            )
            return
        
        # Get active packages for this client
        from .repo_service_packages import list_packages
        packages = list_packages(self.db_path, client_id=client_id, active=True, limit=10)
        
        if not packages:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, no packages are currently available. Please visit our website for more information."
            )
            return
        
        # Get client for currency symbol
        client = repo.get_client(self.db_path, client_id)
        currency_symbol = "฿"  # Default
        if client:
            geo_country = getattr(client, "geo_country", "").upper()
            if geo_country == "AU":
                currency_symbol = "A$"
            elif geo_country == "US":
                currency_symbol = "$"
            elif geo_country in ["TH", "THA"]:
                currency_symbol = "฿"
        
        # Build numbered package list
        message = "📦 Here are our available packages:\n\n"
        package_list = []
        for idx, pkg in enumerate(packages, 1):
            message += f"{idx}. {pkg.name}\n"
            message += f"   💰 {currency_symbol}{pkg.price:.0f} | ⏱️ {pkg.duration_min} min\n\n"
            package_list.append({
                "number": idx,
                "package_id": pkg.package_id,
                "name": pkg.name
            })
        
        message += "Please reply with the number (1, 2, 3, etc.) to select a package."
        
        await self.send_message(conversation.external_thread_id, message)
        
        # Store package list in conversation meta
        conversation_meta = conversation.meta_json.copy()
        conversation_meta["package_list"] = package_list
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
    
    async def handle_package_number_selection(
        self,
        conversation: Any,
        channel: Any,
        number: int
    ) -> None:
        """Handle package selection by number."""
        package_list = conversation.meta_json.get("package_list", [])
        if not package_list:
            await self.send_message(
                conversation.external_thread_id,
                "I don't see a package list. Please send /start to begin."
            )
            return
        
        # Find package by number
        selected_pkg = None
        for pkg in package_list:
            if pkg["number"] == number:
                selected_pkg = pkg
                break
        
        if not selected_pkg:
            await self.send_message(
                conversation.external_thread_id,
                f"Invalid package number. Please choose a number between 1 and {len(package_list)}."
            )
            return
        
        # Get package details (with caching)
        cache_mgr = get_cache_manager()
        cache_key = f"package:{selected_pkg['package_id']}"
        package = await cache_mgr.get(cache_key)
        if package is None:
            package = repo.get_package(self.db_path, selected_pkg["package_id"])
            if package:
                await cache_mgr.set(cache_key, package, ttl_seconds=300)
        if not package:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, the selected package is no longer available. Please choose another."
            )
            return
        
        # Get client for currency symbol
        client_id = channel.meta_json.get("client_id")
        currency_symbol = "฿"  # Default
        if client_id:
            client = repo.get_client(self.db_path, client_id)
            if client:
                geo_country = getattr(client, "geo_country", "").upper()
                if geo_country == "AU":
                    currency_symbol = "A$"
                elif geo_country == "US":
                    currency_symbol = "$"
                elif geo_country in ["TH", "THA"]:
                    currency_symbol = "฿"
        
        # Confirm package selection
        message = f"""✅ You've selected:

📦 {package.name}
💰 {currency_symbol}{package.price:.0f}
⏱️ {package.duration_min} minutes

Is this correct? Reply 'yes' to confirm, or 'no' to choose a different package."""
        
        await self.send_message(conversation.external_thread_id, message)
        
        # Store selected package in conversation meta
        conversation_meta = conversation.meta_json.copy()
        conversation_meta["pending_package_id"] = selected_pkg["package_id"]
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
    
    async def handle_timeslot_selection(
        self,
        conversation: Any,
        channel: Any,
        timeslot_input: str
    ) -> None:
        """Handle timeslot selection and create booking request."""
        # #region agent log
        import json as _json
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","location":"telegram_polling.py:666","message":"handle_timeslot_selection entry","data":{"instance_id":self.instance_id,"chat_id":conversation.external_thread_id,"timeslot_input":timeslot_input,"pending_package_id":conversation.meta_json.get("pending_package_id"),"booking_state":conversation.meta_json.get("booking_state")},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        package_id = conversation.meta_json.get("pending_package_id")
        if not package_id:
            await self.send_message(
                conversation.external_thread_id,
                "I don't see a selected package. Please start over with /start."
            )
            return
        
        # Normalize timeslot input
        normalized_timeslot = self._normalize_timeslot(timeslot_input, conversation)
        if not normalized_timeslot:
            await self.send_message(
                conversation.external_thread_id,
                "I didn't understand that time window. Please reply with 'morning', 'afternoon', 'evening', or a number (1, 2, 3)."
            )
            return
        
        # Get package
        # Get package (with caching)
        cache_mgr = get_cache_manager()
        cache_key = f"package:{package_id}"
        package = await cache_mgr.get(cache_key)
        if package is None:
            package = repo.get_package(self.db_path, package_id)
            if package:
                await cache_mgr.set(cache_key, package, ttl_seconds=300)
        if not package:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, the selected package is no longer available."
            )
            return
        
        # Get or create lead from Telegram user info
        chat_id = conversation.external_thread_id
        username = conversation.meta_json.get("telegram_username")
        client_id = channel.meta_json.get("client_id") or (package.client_id if package else None)
        
        lead_id = await self._get_or_create_lead_from_telegram(
            chat_id, username, client_id
        )
        
        if not lead_id:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, there was an error creating your booking. Please try again."
            )
            return

        if not client_id:
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, this channel is not configured for bookings. Please contact support."
            )
            return

        # V1 duplicate check removed - now handled by BookingService
        # existing_booking = get_recent_booking_request(
        #     self.db_path,
        #     lead_id=lead_id,
        #     package_id=package_id,
        #     preferred_window=normalized_timeslot,
        #     within_seconds=30
        # )
        # V1 duplicate response block removed
        # if existing_booking:
        #     ... (old V1 code)
        #     return
        existing_booking = None  # Ensure variable is defined for lint
        
        # Check booking creation cooldown (10 seconds per chat_id)
        current_time = time.time()
        last_booking_time = await self.state_manager.get_booking_cooldown(chat_id)
        if current_time - last_booking_time < 10.0:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"telegram_polling.py:730","message":"booking creation blocked by cooldown","data":{"instance_id":self.instance_id,"chat_id":chat_id,"time_since_last":current_time-last_booking_time},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            await self.send_message(
                conversation.external_thread_id,
                "Please wait a moment before creating another booking. Your previous booking is being processed."
            )
            return
        
        # Clear conversation state BEFORE booking creation to prevent race conditions
        conversation_meta = conversation.meta_json.copy()
        conversation_meta.pop("pending_package_id", None)
        conversation_meta.pop("booking_state", None)
        conversation_meta.pop("timeslot_list", None)
        get_or_create_conversation(
            self.db_path,
            conversation_id=conversation.conversation_id,
            channel_id=conversation.channel_id,
            external_thread_id=conversation.external_thread_id,
            meta_json=conversation_meta
        )
        
        # Generate booking request ID
        request_id = self._generate_booking_request_id(chat_id)
        
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"B","location":"telegram_polling.py:715","message":"before booking creation","data":{"instance_id":self.instance_id,"chat_id":chat_id,"lead_id":lead_id,"package_id":package_id,"normalized_timeslot":normalized_timeslot},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # V2: Use BookingService to create booking
        try:
            # Get or create customer from lead
            from .repo_bookings import get_customer_by_telegram_id, create_customer_from_lead
            from .repo_leads import get_lead
            
            # Try to find existing customer by telegram_id
            customer = get_customer_by_telegram_id(self.db_path, chat_id)
            
            if not customer:
                # Create customer from lead
                lead = get_lead(self.db_path, lead_id)
                if not lead:
                    raise ValueError(f"Lead {lead_id} not found")
                
                customer = create_customer_from_lead(
                    self.db_path,
                    lead_id=lead_id,
                    telegram_id=chat_id,
                    telegram_username=username
                )
            
            # Create booking using BookingService
            booking_service = BookingService(self.db_path)
            booking = booking_service.create_booking_for_customer(
                customer_id=customer.customer_id,
                client_id=client_id,
                channel="telegram_bot",
                package_id=package_id,
                preferred_time_window=normalized_timeslot,
                lead_id=lead_id,
            )
            
            # Update booking creation cooldown
            await self.state_manager.set_booking_cooldown(chat_id, current_time)
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"C","location":"telegram_polling.py:780","message":"booking created successfully","data":{"instance_id":self.instance_id,"chat_id":chat_id,"booking_id":booking.booking_id,"customer_id":customer.customer_id,"package_id":package_id},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            # Notify vendor bot
            await self.notify_vendor_bot(booking, lead_id)
            
            # Confirm to customer
            message = f"""✅ Your booking request has been created!

📋 Booking ID: {booking.booking_id}
📦 Package: {package.name}
⏰ Preferred time: {normalized_timeslot}

We'll confirm your appointment shortly. You'll receive a notification once it's confirmed."""
            
            await self.send_message(conversation.external_thread_id, message)
        except Exception as e:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"C","location":"telegram_polling.py:763","message":"booking creation failed","data":{"instance_id":self.instance_id,"chat_id":chat_id,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [ERROR] Error creating booking: {e}")
            await self.send_message(
                conversation.external_thread_id,
                "Sorry, there was an error creating your booking. Please try again later."
            )
    
    async def notify_vendor_bot(
        self,
        booking: Booking,
        lead_id: int
    ) -> None:
        """Notify vendor bot about new booking request."""
        try:
            # #region agent log
            import json as _json
            import time as _time
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:762","message":"notify_vendor_bot called","data":{"instance_id":self.instance_id,"booking_id":booking.booking_id,"lead_id":lead_id},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            # Find vendor bot channel
            channels = list_chat_channels(self.db_path, provider=ChatProvider.telegram, limit=10)
            vendor_channel = None
            for ch in channels:
                if ch.meta_json.get("bot_type") == "vendor" and ch.meta_json.get("telegram_bot_token"):
                    vendor_channel = ch
                    break
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:777","message":"vendor channel lookup","data":{"instance_id":self.instance_id,"vendor_channel_found":vendor_channel is not None,"channel_id":vendor_channel.channel_id if vendor_channel else None,"has_token":vendor_channel.meta_json.get("telegram_bot_token") is not None if vendor_channel else False},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            if not vendor_channel:
                safe_print("[TelegramPolling] [INFO] No vendor bot configured, skipping notification")
                return
            
            # Get lead info
            lead = get_lead(self.db_path, lead_id)
            customer_name = lead.name if lead and lead.name else "Customer"
            customer_username = lead.meta_json.get("telegram_username") if lead and lead.meta_json else None
            
            # Get package info (with caching)
            cache_mgr = get_cache_manager()
            cache_key = f"package:{booking.package_id}"
            package = await cache_mgr.get(cache_key)
            if package is None:
                package = repo.get_package(self.db_path, booking.package_id)
                if package:
                    await cache_mgr.set(cache_key, package, ttl_seconds=300)
            package_name = package.name if package else booking.package_id
            
            # Build notification message
            message = f"""🔔 New Booking Request

📋 Booking ID: {booking.booking_id}
📦 Package: {package_name}
👤 Customer: {customer_name}"""
            
            if customer_username:
                message += f" (@{customer_username})"
            
            message += f"""
⏰ Preferred time: {booking.preferred_time_window or "Not specified"}

Use /confirm_{booking.booking_id} to confirm this booking."""
            
            # Send to vendor bot
            vendor_client = TelegramPollingClient(
                vendor_channel.meta_json.get("telegram_bot_token"),
                self.db_path,
                client_id=None
            )
            
            # Find vendor bot's chat ID (this would typically be stored in channel meta or a separate config)
            # For now, we'll try to send to a known vendor chat ID if available
            vendor_chat_id = vendor_channel.meta_json.get("vendor_chat_id")
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:815","message":"vendor_chat_id check","data":{"instance_id":self.instance_id,"vendor_chat_id":vendor_chat_id,"has_vendor_chat_id":vendor_chat_id is not None},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            if vendor_chat_id:
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:817","message":"sending vendor notification","data":{"instance_id":self.instance_id,"vendor_chat_id":str(vendor_chat_id),"booking_id":booking.booking_id},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
                await vendor_client.send_message(str(vendor_chat_id), message)
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:818","message":"vendor notification sent","data":{"instance_id":self.instance_id,"vendor_chat_id":str(vendor_chat_id)},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
            else:
                safe_print(f"[TelegramPolling] [WARN] No vendor_chat_id configured for vendor bot, cannot send notification")
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"G","location":"telegram_polling.py:819","message":"vendor notification skipped - no vendor_chat_id","data":{"instance_id":self.instance_id,"channel_id":vendor_channel.channel_id,"meta_keys":list(vendor_channel.meta_json.keys())},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
        except Exception as e:
            safe_print(f"[TelegramPolling] [ERROR] Error notifying vendor bot: {e}")
    
    def _normalize_timeslot(self, input_text: str, conversation: Any) -> Optional[str]:
        """Normalize timeslot input to standard format."""
        input_lower = input_text.strip().lower()
        
        # Check if it's a number (1, 2, 3)
        if input_lower.isdigit():
            num = int(input_lower)
            timeslot_list = conversation.meta_json.get("timeslot_list", [])
            for slot in timeslot_list:
                if slot.get("number") == num:
                    return slot.get("normalized")
            # Fallback mapping
            if num == 1:
                return "Morning (9am-12pm)"
            elif num == 2:
                return "Afternoon (12pm-5pm)"
            elif num == 3:
                return "Evening (5pm-9pm)"
        
        # Check for text matches
        if input_lower in ["morning", "1"]:
            return "Morning (9am-12pm)"
        elif input_lower in ["afternoon", "2"]:
            return "Afternoon (12pm-5pm)"
        elif input_lower in ["evening", "3"]:
            return "Evening (5pm-9pm)"
        
        # If input contains time-related keywords, try to match
        if "morning" in input_lower or "9" in input_lower or "10" in input_lower or "11" in input_lower:
            return "Morning (9am-12pm)"
        elif "afternoon" in input_lower or "12" in input_lower or "1" in input_lower or "2" in input_lower or "3" in input_lower or "4" in input_lower:
            return "Afternoon (12pm-5pm)"
        elif "evening" in input_lower or "5" in input_lower or "6" in input_lower or "7" in input_lower or "8" in input_lower or "9" in input_lower:
            return "Evening (5pm-9pm)"
        
        return None
    
    async def _get_or_create_lead_from_telegram(
        self,
        chat_id: str,
        username: Optional[str],
        client_id: Optional[str]
    ) -> Optional[int]:
        """Get or create lead from Telegram user info using optimized indexed lookup."""
        try:
            # Use atomic get-or-create function with indexed telegram_chat_id column
            lead_id = get_or_create_lead_by_telegram_chat_id(
                self.db_path,
                telegram_chat_id=chat_id,
                username=username,
                client_id=client_id,
                source="telegram_bot"
            )
            return lead_id
        except Exception as e:
            safe_print(f"[TelegramPolling] [ERROR] Error creating/getting lead: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_booking_request_id(self, chat_id: str) -> str:
        """Generate unique booking request ID."""
        timestamp = int(time.time() * 1000)  # milliseconds
        return f"br_telegram_{chat_id}_{timestamp}"
    
    async def handle_vendor_command(self, chat_id: str, text: str, channel: Any) -> None:
        """Handle vendor bot commands for managing bookings.
        
        Args:
            chat_id: Telegram chat ID of the sender
            text: Command text
            channel: ChatChannel object for vendor bot (contains vendor_chat_id in meta_json)
        """
        text = text.strip()
        
        # P0 SECURITY FIX: Check authorization - only allow commands from authorized vendor chat_id
        vendor_chat_id = channel.meta_json.get("vendor_chat_id")
        if vendor_chat_id and str(chat_id) != str(vendor_chat_id):
            # Unauthorized access attempt - log and deny
            safe_print(f"[TelegramPolling] [SECURITY] Unauthorized vendor command attempt from chat_id: {chat_id} (expected: {vendor_chat_id})")
            # Log unauthorized attempt (best-effort)
            try:
                import json as _json
                import time as _time
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"audit-fix","hypothesisId":"SECURITY","location":"telegram_polling.py:1255","message":"unauthorized_vendor_command_attempt","data":{"instance_id":self.instance_id,"chat_id":chat_id,"expected_vendor_chat_id":vendor_chat_id,"command":text[:50]},"timestamp":int(_time.time()*1000)})+"\n")
            except Exception as e:
                safe_print(f"[TelegramPolling] [WARN] Failed to log unauthorized attempt: {e}")
            
            # Send generic error message (don't reveal authorization details)
            await self.send_message(chat_id, "❌ Unauthorized. This bot is for authorized vendors only.")
            return
        
        # #region agent log
        import json as _json
        import time as _time
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:943","message":"handle_vendor_command called","data":{"instance_id":self.instance_id,"chat_id":chat_id,"text":text},"timestamp":int(_time.time()*1000)})+"\n")
        except Exception as e:
            safe_print(f"[TelegramPolling] [WARN] Failed to log vendor command: {e}")
        # #endregion
        
        if text == "/start" or text == "/help":
            help_text = """🤖 Vendor Bot Commands:

/bookings - List pending bookings
/confirm <booking_id> or /confirm_<booking_id> - Confirm a booking
/paid <payment_id> - Mark payment as paid
/complete <booking_id> - Mark booking as completed

Example:
  /bookings
  /confirm bk_123  or  /confirm_bk_123
  /paid pi_456
  /complete bk_123"""
            await self.send_message(chat_id, help_text)
        
        elif text == "/bookings":
            await self.handle_list_bookings(chat_id)
        
        elif text.startswith("/confirm ") or text.startswith("/confirm_"):
            # Support both: "/confirm bk_xxx" (space) and "/confirm_bk_xxx" (underscore, as shown in notifications)
            if text.startswith("/confirm_"):
                booking_id = text[9:].strip()  # len("/confirm_") == 9
            else:
                booking_id = text.replace("/confirm ", "").strip()
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:965","message":"/confirm command detected","data":{"instance_id":self.instance_id,"chat_id":chat_id,"booking_id":booking_id},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            await self.handle_confirm_booking(chat_id, booking_id)
        
        elif text.startswith("/paid "):
            payment_id = text.replace("/paid ", "").strip()
            await self.handle_mark_paid(chat_id, payment_id)
        
        elif text.startswith("/complete "):
            booking_id = text.replace("/complete ", "").strip()
            await self.handle_complete_booking(chat_id, booking_id)
        
        else:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:977","message":"unknown vendor command","data":{"instance_id":self.instance_id,"chat_id":chat_id,"text":text},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            await self.send_message(chat_id, "Unknown command. Use /help for available commands.")
    
    async def handle_list_bookings(self, chat_id: str) -> None:
        """List pending bookings for vendor."""
        # Get bookings that need vendor action
        from .repo_bookings import get_bookings_by_status, get_customer
        
        # We can look for DEPOSIT_REQUESTED and TIME_WINDOW_SET (which are waiting for confirmation/deposit)
        # And CONFIRMED (for reference)
        
        bookings = get_bookings_by_status(self.db_path, status="DEPOSIT_REQUESTED", limit=10)
        bookings.extend(get_bookings_by_status(self.db_path, status="TIME_WINDOW_SET", limit=10))
        bookings.extend(get_bookings_by_status(self.db_path, status="CONFIRMED", limit=10))
        
        # Sort by updated_at desc
        bookings.sort(key=lambda b: b.updated_at, reverse=True)
        bookings = bookings[:20]
        
        if not bookings:
            await self.send_message(chat_id, "✅ No pending bookings at the moment.")
            return
        
        message = "📋 Recent Bookings:\n\n"
        for booking in bookings:
            customer = get_customer(self.db_path, booking.customer_id)
            customer_name = customer.display_name if customer else "Unknown"
            
            # Payment status from booking directly
            payment_status = ""
            if booking.deposit_status != "none":
                payment_status = f" | Dep: {booking.deposit_status}"
            
            message += f"• {booking.booking_id}\n"
            message += f"  {customer_name} | Status: {booking.status}{payment_status}\n"
            if booking.preferred_time_window:
                message += f"  Time: {booking.preferred_time_window}\n"
            message += "\n"
        
        await self.send_message(chat_id, message)
    
    async def handle_confirm_booking(self, chat_id: str, booking_id: str) -> None:
        """Confirm a booking."""
        svc = BookingService(self.db_path)
        booking = get_booking(self.db_path, booking_id)
        
        if not booking:
            await self.send_message(chat_id, f"❌ Booking '{booking_id}' not found.")
            return
        
        if booking.status == "CONFIRMED":
            await self.send_message(chat_id, f"✅ Booking '{booking_id}' is already confirmed.")
            return
        
        try:
            # Override required if deposit requested but not paid?
            # For simplicity, vendor confirm = override
            svc.confirm_booking(booking_id, actor_id="telegram_vendor", override_reason="vendor_manual_confirm")
            
            await self.send_message(chat_id, f"✅ Booking '{booking_id}' confirmed!")
            
            # Notify customer about confirmation
            # Refetch to get updated state if needed, but we have enough info
            # We need to notify customer.
            await self._notify_customer_booking_confirmed(booking)
            
        except Exception as e:
            safe_print(f"[TelegramPolling] [ERROR] Failed to confirm booking {booking_id}: {e}")
            await self.send_message(chat_id, f"❌ Failed to confirm booking: {e}")
    
    async def _notify_customer_booking_confirmed(self, booking: Booking) -> None:
        """Notify customer that their booking has been confirmed."""
        try:
            # Get customer
            from .repo_bookings import get_customer
            customer = get_customer(self.db_path, booking.customer_id)
            if not customer:
                 safe_print(f"[TelegramPolling] [WARN] Customer not found for booking {booking.booking_id}")
                 return

            customer_chat_id = customer.telegram_id
            
            if not customer_chat_id:
                safe_print(f"[TelegramPolling] [WARN] No telegram_id for customer {customer.customer_id}")
                return
            
            # Find customer bot channel (same logic as before)
            channels = list_chat_channels(self.db_path, provider=ChatProvider.telegram, limit=10)
            customer_channel = None
            for ch in channels:
                 # Logic: find non-vendor bot with token
                 if ch.meta_json.get("bot_type") != "vendor" and ch.meta_json.get("telegram_bot_token"):
                     customer_channel = ch
                     break
            
            if not customer_channel:
                safe_print(f"[TelegramPolling] [WARN] No customer bot channel found")
                return
            
            customer_client = TelegramPollingClient(
                customer_channel.meta_json.get("telegram_bot_token"),
                self.db_path,
                client_id=None
            )
            
            message = f"""✅ Great news! Your booking has been confirmed!

📋 Booking ID: {booking.booking_id}
📦 Package: {booking.package_name_snapshot}
⏰ Preferred time: {booking.preferred_time_window or 'Not specified'}

We're looking forward to serving you!"""
            
            await customer_client.send_message(str(customer_chat_id), message)
            
        except Exception as e:
            safe_print(f"[TelegramPolling] [ERROR] Error notifying customer of confirmation: {e}")
            customer_chat_id = booking.meta_json.get("telegram_chat_id")
            if not customer_chat_id:
                # #region agent log
                import json as _json
                import time as _time
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:1040","message":"customer notification skipped - no telegram_chat_id","data":{"instance_id":self.instance_id,"booking_id":booking.request_id},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
                safe_print(f"[TelegramPolling] [WARN] No telegram_chat_id in booking meta, cannot notify customer")
                return
            
            # Get package info (with caching)
            cache_mgr = get_cache_manager()
            cache_key = f"package:{booking.package_id}"
            package = await cache_mgr.get(cache_key)
            if package is None:
                package = repo.get_package(self.db_path, booking.package_id)
                if package:
                    await cache_mgr.set(cache_key, package, ttl_seconds=300)
            package_name = package.name if package else booking.package_id
            
            # Find customer bot channel
            channels = list_chat_channels(self.db_path, provider=ChatProvider.telegram, limit=10)
            customer_channel = None
            for ch in channels:
                if ch.meta_json.get("bot_type") != "vendor" and ch.meta_json.get("telegram_bot_token"):
                    customer_channel = ch
                    break
            
            if not customer_channel:
                safe_print(f"[TelegramPolling] [WARN] No customer bot channel found, cannot notify customer")
                return
            
            # Create customer bot client
            customer_client = TelegramPollingClient(
                customer_channel.meta_json.get("telegram_bot_token"),
                self.db_path,
                client_id=None
            )
            
            # Send confirmation message to customer
            message = f"""✅ Great news! Your booking has been confirmed!

📋 Booking ID: {booking.request_id}
📦 Package: {package_name}
⏰ Preferred time: {booking.preferred_window or 'Not specified'}

We're looking forward to serving you!"""
            
            # #region agent log
            import json as _json
            import time as _time
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:1068","message":"sending customer confirmation","data":{"instance_id":self.instance_id,"booking_id":booking.request_id,"customer_chat_id":str(customer_chat_id)},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
            
            await customer_client.send_message(str(customer_chat_id), message)
            
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:1070","message":"customer confirmation sent","data":{"instance_id":self.instance_id,"booking_id":booking.request_id},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
        except Exception as e:
            safe_print(f"[TelegramPolling] [ERROR] Error notifying customer of confirmation: {e}")
            # #region agent log
            import json as _json
            import time as _time
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"H","location":"telegram_polling.py:1074","message":"customer notification error","data":{"instance_id":self.instance_id,"booking_id":booking.request_id,"error":str(e)},"timestamp":int(_time.time()*1000)})+"\n")
            except: pass
            # #endregion
    
    async def handle_mark_paid(self, chat_id: str, payment_id: str) -> None:
        """Mark payment intent as paid."""
        payment_intent = get_payment_intent(self.db_path, payment_id)
        if not payment_intent:
            await self.send_message(chat_id, f"❌ Payment intent '{payment_id}' not found.")
            return
        
        if payment_intent.status == "paid":
            await self.send_message(chat_id, f"✅ Payment '{payment_id}' is already marked as paid.")
            return
        
        updated = mark_payment_intent_paid(self.db_path, payment_id)
        if updated:
            await self.send_message(
                chat_id,
                f"✅ Payment '{payment_id}' marked as paid!\n"
                f"Amount: ฿{payment_intent.amount:.0f}\n"
                f"Booking automatically confirmed."
            )
        else:
            await self.send_message(chat_id, f"❌ Failed to mark payment '{payment_id}' as paid.")
    
    async def handle_complete_booking(self, chat_id: str, booking_id: str) -> None:
        """Mark booking as completed."""
        svc = BookingService(self.db_path)
        booking = get_booking(self.db_path, booking_id)
        
        if not booking:
            await self.send_message(chat_id, f"❌ Booking '{booking_id}' not found.")
            return
            
        if booking.status == "COMPLETE":
            await self.send_message(chat_id, f"✅ Booking '{booking_id}' is already completed.")
            return
            
        try:
             svc.mark_complete(booking_id, actor_id="telegram_vendor")
             await self.send_message(chat_id, f"✅ Booking '{booking_id}' marked as completed!")
        except Exception as e:
             safe_print(f"[TelegramPolling] [ERROR] Failed to complete booking {booking_id}: {e}")
             await self.send_message(chat_id, f"❌ Failed to complete booking: {e}")
    
    async def poll_loop(self) -> None:
        """Main polling loop."""
        self.running = True
        # #region agent log
        import json as _json
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"C","location":"telegram_polling.py:1006","message":"poll_loop started","data":{"instance_id":self.instance_id,"bot_token_prefix":self.bot_token[:10],"client_id":self.client_id},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        safe_print(f"[TelegramPolling] [INFO] Starting polling for bot token: {self.bot_token[:20]}...")
        safe_print(f"[TelegramPolling] [INFO] Bot will receive messages automatically (no webhook needed)")
        
        # CRITICAL: Check and delete any existing webhook before starting polling
        # If a webhook is set, polling won't work
        try:
            # First check webhook status
            webhook_response = await self.client.get(f"{self.api_url}/getWebhookInfo")
            webhook_data = webhook_response.json()
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:1493","message":"webhook info check","data":{"instance_id":self.instance_id,"ok":webhook_data.get("ok"),"url":webhook_data.get("result",{}).get("url"),"pending_update_count":webhook_data.get("result",{}).get("pending_update_count")},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            webhook_url = ""
            pending_count = 0
            if webhook_data.get("ok"):
                webhook_info = webhook_data.get("result", {})
                webhook_url = webhook_info.get("url", "")
                pending_count = webhook_info.get("pending_update_count", 0)
                if webhook_url:
                    safe_print(f"[TelegramPolling] [WARN] Webhook is still active: {webhook_url} (pending updates: {pending_count})")
                    # Only drop pending updates if webhook exists (to clean up old webhook updates)
                    safe_print(f"[TelegramPolling] [INFO] Deleting webhook and dropping {pending_count} pending update(s)...")
                    delete_response = await self.client.get(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": True})
                    delete_data = delete_response.json()
                else:
                    safe_print(f"[TelegramPolling] [OK] No webhook is set (pending updates: {pending_count})")
                    # CRITICAL FIX: Even without webhook, use drop_pending_updates=True to reset Telegram's update state
                    # This clears any confirmed updates from previous runs that might block new updates
                    # Without this, if previous runs used offset=0, Telegram might think all updates are confirmed
                    safe_print(f"[TelegramPolling] [INFO] Resetting update state by dropping pending updates...")
                    delete_response = await self.client.get(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": True})
                    delete_data = delete_response.json()
            else:
                # Fallback: delete webhook and reset update state
                safe_print(f"[TelegramPolling] [INFO] Fallback: deleting webhook and resetting update state...")
                delete_response = await self.client.get(f"{self.api_url}/deleteWebhook", params={"drop_pending_updates": True})
                delete_data = delete_response.json()
            # #region agent log
            try:
                # Determine if we actually dropped pending updates
                actually_dropped = False
                if webhook_url:
                    actually_dropped = True  # We used drop_pending_updates=True when webhook existed
                else:
                    # Check if we used drop_pending_updates=True in the no-webhook path
                    # (We now always use it, so this should be True)
                    actually_dropped = True
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H11","location":"telegram_polling.py:1781","message":"webhook deletion attempt","data":{"instance_id":self.instance_id,"ok":delete_data.get("ok"),"description":delete_data.get("description"),"had_webhook":bool(webhook_url),"dropped_pending":actually_dropped},"timestamp":int(time.time()*1000)})+"\n")
            except Exception as log_err:
                safe_print(f"[TelegramPolling] [WARN] Failed to log webhook deletion: {log_err}")
            # #endregion
            if delete_data.get("ok"):
                if webhook_url:
                    safe_print(f"[TelegramPolling] [OK] Deleted webhook and dropped pending updates")
                else:
                    safe_print(f"[TelegramPolling] [OK] Deleted webhook and reset update state (ready for fresh polling)")
                
                # CRITICAL: Wait for Telegram to process the update state reset
                # Telegram needs time to clear confirmed updates and reset the offset state
                # Without this delay, we might start polling before Telegram has finished resetting
                safe_print(f"[TelegramPolling] [INFO] Waiting 2 seconds for Telegram to process update state reset...")
                await asyncio.sleep(2.0)  # Longer wait for Telegram to process the reset
                
                # CRITICAL: Verify webhook is actually deleted before proceeding
                # Sometimes Telegram needs a moment to process the deletion
                await asyncio.sleep(0.5)  # Brief wait for Telegram to process
                verify_response = await self.client.get(f"{self.api_url}/getWebhookInfo")
                verify_data = verify_response.json()
                if verify_data.get("ok"):
                    verify_info = verify_data.get("result", {})
                    verify_url = verify_info.get("url", "")
                    if verify_url:
                        safe_print(f"[TelegramPolling] [ERROR] Webhook still active after deletion: {verify_url}")
                        safe_print(f"[TelegramPolling] [ERROR] Polling will fail with 409 Conflict. Please delete webhook manually.")
                    else:
                        safe_print(f"[TelegramPolling] [OK] Webhook deletion verified")
            else:
                safe_print(f"[TelegramPolling] [WARN] Failed to delete webhook: {delete_data.get('description')}")
                # Try to verify anyway
                verify_response = await self.client.get(f"{self.api_url}/getWebhookInfo")
                verify_data = verify_response.json()
                if verify_data.get("ok"):
                    verify_info = verify_data.get("result", {})
                    verify_url = verify_info.get("url", "")
                    if verify_url:
                        safe_print(f"[TelegramPolling] [ERROR] Webhook is still active: {verify_url}")
                        safe_print(f"[TelegramPolling] [ERROR] Polling will fail. Please delete webhook manually or fix deletion.")
            
            # Reset last_update_id and reset poll flags to start fresh (will get latest updates on next poll)
            # This ensures we don't process any old updates that might have been queued
            self.last_update_id = 0
            self._reset_poll_done = False
            self._drain_poll_done = False
            safe_print(f"[TelegramPolling] [INFO] Reset update offset to 0 for fresh start")
            
            # CRITICAL: Do an initial "drain" poll to consume and discard any remaining old updates
            # This ensures we skip past any updates that weren't dropped by deleteWebhook
            safe_print(f"[TelegramPolling] [INFO] Draining any remaining old updates...")
            try:
                # #region agent log
                import json as _json
                import time as _time
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H1","location":"telegram_polling.py:1690","message":"drain poll starting","data":{"instance_id":self.instance_id,"last_update_id_before":self.last_update_id},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
                drain_updates = await self.get_updates(timeout=1, is_drain_poll=True)
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H1","location":"telegram_polling.py:1695","message":"drain poll completed","data":{"instance_id":self.instance_id,"drain_count":len(drain_updates),"drain_update_ids":[u.get("update_id") for u in drain_updates]},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
                if drain_updates:
                    # Get the highest update_id from the drained updates and set it as our starting point
                    # This ensures we skip all these old updates
                    max_drained_id = max(update.get("update_id", 0) for update in drain_updates)
                    self.last_update_id = max_drained_id
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"debug","hypothesisId":"H1","location":"telegram_polling.py:1700","message":"drain poll set offset","data":{"instance_id":self.instance_id,"max_drained_id":max_drained_id,"new_last_update_id":self.last_update_id,"next_offset":self.last_update_id+1},"timestamp":int(_time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    safe_print(f"[TelegramPolling] [INFO] Drained {len(drain_updates)} old update(s), skipping to offset {self.last_update_id + 1}")
                else:
                    safe_print(f"[TelegramPolling] [OK] No old updates to drain")
                # Mark that drain poll is done - this means we should NOT use offset=-1 in main polling
                # because drain poll already handled any old updates, and offset=-1 would clear new updates
                self._drain_poll_done = True
            except Exception as drain_err:
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H1","location":"telegram_polling.py:1705","message":"drain poll error","data":{"instance_id":self.instance_id,"error":str(drain_err)},"timestamp":int(_time.time()*1000)})+"\n")
                except: pass
                # #endregion
                safe_print(f"[TelegramPolling] [WARN] Error draining old updates: {drain_err}")
                # Continue anyway - we'll rely on offset progression
        except Exception as e:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:1512","message":"webhook deletion error","data":{"instance_id":self.instance_id,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [WARN] Error deleting webhook: {e}")
        
        # Test bot token validity by calling getMe
        try:
            me_response = await self.client.get(f"{self.api_url}/getMe")
            me_data = me_response.json()
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:1475","message":"bot token validation (getMe)","data":{"instance_id":self.instance_id,"ok":me_data.get("ok"),"bot_username":me_data.get("result",{}).get("username"),"bot_id":me_data.get("result",{}).get("id"),"error_description":me_data.get("description")},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            if me_data.get("ok"):
                bot_info = me_data.get("result", {})
                safe_print(f"[TelegramPolling] [OK] Bot token valid - Bot: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
            else:
                safe_print(f"[TelegramPolling] [ERROR] Bot token invalid: {me_data.get('description')}")
        except Exception as e:
            # #region agent log
            try:
                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                    _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:1485","message":"getMe error","data":{"instance_id":self.instance_id,"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            safe_print(f"[TelegramPolling] [WARN] Error validating bot token: {e}")
        
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"run1","hypothesisId":"K","location":"telegram_polling.py:1445","message":"poll_loop starting - clearing stale locks","data":{"instance_id":self.instance_id},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        # CRITICAL: Clear all stale locks and state on startup for clean local dev
        # This ensures old messages don't block new ones
        safe_print(f"[TelegramPolling] [INFO] Clearing stale locks, state, and processed message IDs...")
        await self.state_manager.clear_start_locks()
        # Also clear any stale processing locks and processed message IDs that might block new messages
        await self.state_manager.clear_all_locks()
        safe_print(f"[TelegramPolling] [OK] Cleared all stale locks and processed message history")
        
        safe_print(f"[TelegramPolling] [OK] Polling started - bot is ready to receive messages")
        safe_print(f"[TelegramPolling] [INFO] Send /start to the bot to test")
        safe_print(f"[TelegramPolling] [NOTE] Note: When clicking deep links, make sure to click 'Start' button in Telegram")
        
        poll_count = 0
        last_update_time = time.time()
        while self.running:
            try:
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H2","location":"telegram_polling.py:1758","message":"poll_loop iteration starting","data":{"instance_id":self.instance_id,"poll_count":poll_count,"last_update_id":self.last_update_id,"next_offset":self.last_update_id+1},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                updates = await self.get_updates(timeout=10)
                poll_count += 1
                
                # #region agent log
                try:
                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H2","location":"telegram_polling.py:1763","message":"poll_loop got updates","data":{"instance_id":self.instance_id,"poll_count":poll_count,"update_count":len(updates),"update_ids":[u.get("update_id") for u in updates]},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                
                # Log polling activity every 10 polls (every ~100 seconds) to show it's alive
                if poll_count % 10 == 0:
                    time_since_update = time.time() - last_update_time
                    safe_print(f"[TelegramPolling] [INFO] Polling active - checked {poll_count} times, waiting for messages... (last update: {time_since_update:.0f}s ago)")
                
                if updates:
                    last_update_time = time.time()
                
                if updates:
                    safe_print(f"[TelegramPolling] [OK] Received {len(updates)} update(s)!")
                    # Log first update details for debugging
                    if updates:
                        first_update = updates[0]
                        update_type = "message" if "message" in first_update else "callback_query" if "callback_query" in first_update else "unknown"
                        safe_print(f"[TelegramPolling] [INFO] First update type: {update_type}, update_id: {first_update.get('update_id')}")
                
                # Reset consecutive error counter on successful poll
                self._consecutive_network_errors = 0
                
                # P0 FIX: Process updates and track successful processing for offset advancement
                processed_update_ids = []
                for update in updates:
                    update_id = update.get("update_id")
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"run1","hypothesisId":"A","hypothesisId":"D","location":"telegram_polling.py:1014","message":"processing update in poll_loop","data":{"instance_id":self.instance_id,"update_id":update_id,"has_message":"message" in update,"has_callback":"callback_query" in update},"timestamp":int(time.time()*1000)})+"\n")
                    except Exception as e:
                        safe_print(f"[TelegramPolling] [WARN] Failed to log update processing: {e}")
                    # #endregion
                    try:
                        if "message" in update:
                            # Pass update_id to handle_message
                            message_with_update_id = update["message"].copy()
                            message_with_update_id["update_id"] = update_id
                            chat_id = message_with_update_id.get('chat', {}).get('id')
                            message_text = message_with_update_id.get('text', '')[:50]
                            safe_print(f"[TelegramPolling] [OK] Processing message from chat_id: {chat_id}, text: '{message_text}...'")
                            # #region agent log
                            try:
                                with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                    _f.write(_json.dumps({"runId":"debug","hypothesisId":"H3","location":"telegram_polling.py:1795","message":"calling handle_message","data":{"instance_id":self.instance_id,"update_id":update_id,"chat_id":chat_id,"message_id":message_with_update_id.get("message_id"),"text_preview":message_text},"timestamp":int(time.time()*1000)})+"\n")
                            except: pass
                            # #endregion
                            try:
                                await self.handle_message(message_with_update_id)
                                # #region agent log
                                try:
                                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H3","location":"telegram_polling.py:1800","message":"handle_message completed successfully","data":{"instance_id":self.instance_id,"update_id":update_id,"chat_id":chat_id},"timestamp":int(time.time()*1000)})+"\n")
                                except: pass
                                # #endregion
                                # Mark as successfully processed only if no exception
                                processed_update_ids.append(update_id)
                            except Exception as msg_error:
                                # #region agent log
                                try:
                                    import traceback as _tb
                                    with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                                        _f.write(_json.dumps({"runId":"debug","hypothesisId":"H3","location":"telegram_polling.py:1805","message":"handle_message failed","data":{"instance_id":self.instance_id,"update_id":update_id,"chat_id":chat_id,"error":str(msg_error),"error_type":type(msg_error).__name__,"traceback":_tb.format_exc()},"timestamp":int(time.time()*1000)})+"\n")
                                except: pass
                                # #endregion
                                # P1 FIX: Log error but don't mark as processed (will retry)
                                safe_print(f"[TelegramPolling] [ERROR] Error handling message from chat_id {chat_id}: {msg_error}")
                                import traceback
                                safe_print(f"[TelegramPolling] [ERROR] Message handling traceback: {traceback.format_exc()}")
                                # Don't append to processed_update_ids - will retry on next poll
                        elif "callback_query" in update:
                            # TODO: Handle callback queries
                            # For now, mark as processed to avoid reprocessing
                            processed_update_ids.append(update_id)
                            pass
                    except Exception as e:
                        # P1 FIX: Log error but don't crash - continue processing other updates
                        safe_print(f"[TelegramPolling] [ERROR] Error processing update {update_id}: {e}")
                        import traceback
                        safe_print(f"[TelegramPolling] [ERROR] Traceback: {traceback.format_exc()}")
                        # Don't mark as processed - will retry on next poll
                        # This prevents message loss
                
                # P0 FIX: Only advance offset after successful processing
                if processed_update_ids:
                    new_last_id = max(processed_update_ids)
                    # #region agent log
                    try:
                        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                            _f.write(_json.dumps({"runId":"audit-fix","hypothesisId":"P0","location":"telegram_polling.py:1670","message":"updating last_update_id after successful processing","data":{"instance_id":self.instance_id,"old_last_update_id":self.last_update_id,"new_last_update_id":new_last_id,"processed_count":len(processed_update_ids)},"timestamp":int(time.time()*1000)})+"\n")
                    except Exception as e:
                        safe_print(f"[TelegramPolling] [WARN] Failed to log offset update: {e}")
                    # #endregion
                    self.last_update_id = new_last_id
                    safe_print(f"[TelegramPolling] [INFO] Advanced offset to {new_last_id} after processing {len(processed_update_ids)} update(s)")
            except KeyboardInterrupt:
                safe_print("[TelegramPolling] [INFO] Stopping polling...")
                self.running = False
                break
            except Exception as e:
                safe_print(f"[TelegramPolling] [ERROR] Error in poll loop: {e}")
                import traceback
                safe_print(f"[TelegramPolling] [ERROR] Traceback: {traceback.format_exc()}")
                # Wait before retrying to avoid rapid error loops
                await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """Stop polling."""
        self.running = False
        await self.client.aclose()


async def start_telegram_polling(db_path: str, client_id: Optional[str] = None, bot_type: Optional[str] = None) -> Optional[TelegramPollingClient]:
    """Start Telegram polling for a client or vendor bot.
    
    Args:
        db_path: Database path
        client_id: Client ID for customer bot (optional)
        bot_type: "vendor" for vendor bot, None for customer bot
    """
    channels = list_chat_channels(db_path, provider=ChatProvider.telegram, limit=10)
    if not channels:
        return None
    
    # Find channel by bot_type or client_id (only select channels with tokens)
    channel = None
    if bot_type:
        # Find vendor bot WITH TOKEN
        for ch in channels:
            if ch.meta_json.get("bot_type") == bot_type and ch.meta_json.get("telegram_bot_token"):
                channel = ch
                break
    elif client_id:
        # Find customer bot by client_id WITH TOKEN
        for ch in channels:
            if (ch.meta_json.get("client_id") == client_id 
                and ch.meta_json.get("bot_type") != "vendor"
                and ch.meta_json.get("telegram_bot_token")):
                channel = ch
                break
    
    if not channel:
        # Fallback: use first non-vendor channel WITH TOKEN if looking for customer bot
        if not bot_type:
            for ch in channels:
                if ch.meta_json.get("bot_type") != "vendor":
                    # Only select channels that have a token
                    if ch.meta_json.get("telegram_bot_token"):
                        channel = ch
                        break
        # Or use first channel WITH TOKEN if looking for vendor bot
        if not channel:
            for ch in channels:
                if ch.meta_json.get("telegram_bot_token"):
                    channel = ch
                    break
    
    if not channel:
        safe_print(f"[TelegramPolling] [WARN] No Telegram channel found")
        return None
    
    bot_token = channel.meta_json.get("telegram_bot_token")
    if not bot_token:
        safe_print(f"[TelegramPolling] [WARN] No bot token found for channel {channel.channel_id}")
        return None
    
    client = TelegramPollingClient(bot_token, db_path, client_id=client_id, channel_id=channel.channel_id)
    return client
