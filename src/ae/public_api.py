from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__

from .public_guard import get_cors_allowlist
from .health import router as health_router
from .metrics import metrics_router
from .middleware import RequestIdMiddleware
from .abuse_controls import AbuseControlsMiddleware

from .console_routes_leads import public_router
from .console_routes_qr_public import public_router as qr_public_router
from .console_routes_events_public import public_router as events_public_router
from .console_routes_chat_public import public_router as chat_public_router
from .console_routes_service_packages_public import public_router as service_packages_public_router

app = FastAPI(title="Acquisition Engine Public API", version=__version__)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(AbuseControlsMiddleware)
app.include_router(health_router)
app.include_router(metrics_router)
# Minimal CORS: allow browser-based forms to post leads.
# In production, restrict origins explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowlist(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(public_router)
app.include_router(qr_public_router, prefix="/v1")
app.include_router(events_public_router, prefix="/v1")
app.include_router(chat_public_router, prefix="/v1")
app.include_router(service_packages_public_router)