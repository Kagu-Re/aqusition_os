"""Unified local development server.

Serves:
- Console (Money Board, etc.) on /console
- Public API on /api and /v1/*
- Landing pages on /pages/{page_id}
- Telegram bot polling (background - no webhook needed)
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__
from .middleware import RequestIdMiddleware
from .abuse_controls import AbuseControlsMiddleware
from .tenant import TenantResolutionMiddleware

# Console routes (include all from console_app)
from .console_routes_auth import router as auth_router
from .console_routes_spend import router as spend_router
from .console_routes_clients import router as clients_router
from .console_routes_pages import router as pages_router
from .console_routes_leads import admin_router as leads_router, public_router as leads_public_router
from .console_routes_abuse import router as abuse_router
from .console_routes_abuse_top import router as abuse_top_router
from .console_routes_onboarding import router as onboarding_router
from .console_routes_timeline import router as timeline_router
from .console_routes_state import router as state_router
from .console_routes_booking_timeline import router as booking_timeline_router
from .console_routes_payments import admin_router as payments_router
from .console_routes_chat_channels import admin_router as chat_channels_router
from .console_routes_chat_conversations import admin_router as chat_conversations_router
from .console_routes_chat_templates import admin_router as chat_templates_router
from .console_routes_chat_automations import admin_router as chat_automations_router
from .console_routes_menus import router as menus_router
from .console_routes_service_packages import admin_router as service_packages_admin_router
from .console_routes_booking_requests import admin_router as booking_requests_router
from .console_routes_payment_intents import admin_router as payment_intents_router
from .console_routes_money_board import admin_router as money_board_router
from .console_routes_qr import router as qr_router
from .console_routes_gov import router as gov_router
from .console_routes_retries import admin_router as retries_router
from .console_routes_exports import router as exports_router
from .console_routes_integrity import router as integrity_router
from .console_routes_events import router as events_router
from .console_routes_alerts import router as alerts_router
from .console_routes_stats import router as stats_router
from .console_routes_bulk import router as bulk_router
from .console_routes_analytics import router as analytics_router
from .health import router as health_router
from .metrics import metrics_router

# Public API routes
from .console_routes_leads import public_router
from .console_routes_qr_public import public_router as qr_public_router
from .console_routes_events_public import public_router as events_public_router
from .console_routes_chat_public import public_router as chat_public_router
from .console_routes_service_packages_public import public_router as service_packages_public_router

# Telegram polling
from .telegram_polling import start_telegram_polling

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
                arg = arg.replace("✅", "[OK]").replace("⚠️", "[WARN]").replace("❌", "[ERROR]")
            safe_args.append(arg)
        print(*safe_args, **kwargs)

# Create unified app
app = FastAPI(title="Acquisition Engine Local Dev Server", version=__version__)

# Add middleware (tenant must run early for request.state.tenant_id)
# Middleware always added; checks is_multi_tenant_enabled() at request time
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TenantResolutionMiddleware)
app.add_middleware(AbuseControlsMiddleware)

# Add no-cache middleware for development
@app.middleware("http")
async def no_cache_middleware(request: Request, call_next):
    """Add no-cache headers to all responses in development."""
    response = await call_next(request)
    # Add no-cache headers to prevent browser caching during development
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all console routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(spend_router)
app.include_router(clients_router)
app.include_router(pages_router)
app.include_router(leads_router)
app.include_router(leads_public_router)  # Public lead intake
app.include_router(abuse_router)
app.include_router(abuse_top_router)
app.include_router(onboarding_router)
app.include_router(timeline_router)
app.include_router(state_router)
app.include_router(booking_timeline_router)
app.include_router(payments_router)
app.include_router(chat_channels_router)
app.include_router(chat_conversations_router)
app.include_router(chat_templates_router)
app.include_router(chat_automations_router)
app.include_router(menus_router)
app.include_router(service_packages_admin_router)
app.include_router(booking_requests_router)
app.include_router(payment_intents_router)
app.include_router(money_board_router)
app.include_router(qr_router)
app.include_router(gov_router)
app.include_router(retries_router)
app.include_router(exports_router)
app.include_router(integrity_router)
app.include_router(events_router)
app.include_router(alerts_router)
app.include_router(stats_router)
app.include_router(bulk_router)
app.include_router(analytics_router)

# Public API routes
app.include_router(public_router)
app.include_router(qr_public_router, prefix="/v1")
app.include_router(events_public_router, prefix="/v1")
app.include_router(chat_public_router, prefix="/v1")
app.include_router(service_packages_public_router)  # Already has /v1 prefix in route definition

# Mount console static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "console_static")
if os.path.isdir(STATIC_DIR):
    app.mount("/console_static", StaticFiles(directory=STATIC_DIR), name="console_static")

# Landing pages directory
LANDING_PAGES_DIR = Path("exports/static_site")


@app.get("/")
def root():
    """Root endpoint - show available services."""
    return {
        "message": "Acquisition Engine Local Dev Server",
        "version": __version__,
        "services": {
            "console": "/console",
            "money_board": "/money-board",
            "public_api": "/api",
            "landing_pages": "/pages/{page_id}",
            "health": "/api/health"
        }
    }

@app.get("/console", response_class=HTMLResponse)
def console():
    """Serve console HTML."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse("<h1>console assets missing</h1>", status_code=500)
    # Return with no-cache headers for development
    response = FileResponse(index_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/money-board", response_class=HTMLResponse)
def money_board():
    """Serve standalone Money Board HTML."""
    mb_path = os.path.join(STATIC_DIR, "money_board.html")
    if not os.path.exists(mb_path):
        return HTMLResponse("<h1>money board assets missing</h1>", status_code=500)
    return FileResponse(mb_path)


@app.get("/client/money-board", response_class=HTMLResponse)
def client_money_board():
    """Serve client-facing Money Board HTML."""
    cmb_path = os.path.join(STATIC_DIR, "client_money_board.html")
    if not os.path.exists(cmb_path):
        return HTMLResponse("<h1>client money board assets missing</h1>", status_code=500)
    return FileResponse(cmb_path)


@app.get("/pages/{page_id}")
@app.get("/pages/{page_id}/")
@app.get("/pages/{page_id}/index.html")
def serve_landing_page(page_id: str):
    """Serve landing page from static site directory."""
    page_path = LANDING_PAGES_DIR / page_id / "index.html"
    
    if not page_path.exists():
        return HTMLResponse(
            f"<h1>Page not found</h1><p>Page '{page_id}' not found in {LANDING_PAGES_DIR}</p><p>Publish a page first: python -m ae.cli publish-page --db acq.db --page-id {page_id}</p>",
            status_code=404
        )
    
    # Return with no-cache headers for development
    response = FileResponse(page_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/pages/{page_id}/assets/{filename}")
def serve_landing_page_asset(page_id: str, filename: str):
    """Serve landing page assets (CSS, JS, images)."""
    asset_path = LANDING_PAGES_DIR / page_id / "assets" / filename
    
    if not asset_path.exists():
        return HTMLResponse(f"<h1>Asset not found</h1>", status_code=404)
    
    # Return with no-cache headers for development
    response = FileResponse(asset_path)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# Telegram polling background task
_telegram_clients: list = []
_polling_started = False  # Guard to prevent multiple polling instances


@app.on_event("startup")
async def startup_event():
    """Start Telegram polling on server startup."""
    global _polling_started
    
    # #region agent log
    import json as _json
    import time as _time
    try:
        with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
            _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"C","location":"local_dev_server.py:202","message":"startup_event called","data":{"existing_clients_count":len(_telegram_clients),"polling_started":_polling_started},"timestamp":int(_time.time()*1000)})+"\n")
    except: pass
    # #endregion
    
    # Prevent multiple polling instances (e.g., from uvicorn --reload)
    # Stop any existing clients first to prevent duplicates
    if _telegram_clients:
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"C","location":"local_dev_server.py:210","message":"stopping existing polling clients","data":{"existing_clients_count":len(_telegram_clients)},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        safe_print("[LocalDevServer] [WARN] Stopping existing Telegram polling clients (likely due to --reload)")
        for client in _telegram_clients:
            try:
                await client.stop()
            except Exception as e:
                print(f"[LocalDevServer] Error stopping client: {e}")
        _telegram_clients.clear()
    
    if _polling_started:
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"C","location":"local_dev_server.py:222","message":"polling already started, skipping","data":{"existing_clients_count":len(_telegram_clients)},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        safe_print("[LocalDevServer] [WARN] Telegram polling already started, skipping (likely due to --reload)")
        return
    
    db_path = os.getenv("AE_DB_PATH", "acq.db")
    
    print("[LocalDevServer] Starting Telegram bot polling...")
    
    # Start customer bot polling
    customer_client = await start_telegram_polling(db_path)
    if customer_client:
        _telegram_clients.append(customer_client)
        # Start polling in background
        asyncio.create_task(customer_client.poll_loop())
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"C","location":"local_dev_server.py:225","message":"customer bot polling started","data":{"instance_id":customer_client.instance_id,"total_clients":len(_telegram_clients)},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        safe_print("[LocalDevServer] [OK] Started Telegram customer bot polling")
    else:
        safe_print("[LocalDevServer] [WARN] No Telegram customer bot configured")
    
    # Start vendor bot polling
    vendor_client = await start_telegram_polling(db_path, bot_type="vendor")
    if vendor_client:
        _telegram_clients.append(vendor_client)
        # Start polling in background
        asyncio.create_task(vendor_client.poll_loop())
        # #region agent log
        try:
            with open(r"d:\aqusition_os\.cursor\debug.log", "a", encoding="utf-8") as _f:
                _f.write(_json.dumps({"runId":"post-fix","hypothesisId":"C","location":"local_dev_server.py:237","message":"vendor bot polling started","data":{"instance_id":vendor_client.instance_id,"total_clients":len(_telegram_clients)},"timestamp":int(_time.time()*1000)})+"\n")
        except: pass
        # #endregion
        safe_print("[LocalDevServer] [OK] Started Telegram vendor bot polling")
    else:
        safe_print("[LocalDevServer] [WARN] No Telegram vendor bot configured")
    
    _polling_started = True


@app.on_event("shutdown")
async def shutdown_event():
    """Stop Telegram polling on server shutdown."""
    global _polling_started
    for client in _telegram_clients:
        await client.stop()
    _telegram_clients.clear()
    _polling_started = False
    print("[LocalDevServer] Stopped Telegram polling")
