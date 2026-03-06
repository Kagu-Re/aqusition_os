from __future__ import annotations

# Operator Console app (FastAPI)
# Shared helpers live in console_support.py. Auth/probes routes live in console_routes_auth.py.

import os
from typing import Optional
from fastapi.responses import RedirectResponse

from .console_support import (
    FastAPI,
    Request,
    Depends,
    HTTPException,
    HTMLResponse,
    FileResponse,
    StaticFiles,
    require_role,
    require_secret,
    _resolve_db,
    _resolve_db_path,
    _coarse_ip_hint,
    _rate_limit_check,
    _MAX_BODY_BYTES,
    _RL_LEAD_PER_HOUR,
    _RL_API_PER_HOUR,
    repo,
)
from . import __version__
from .health import router as health_router
from .metrics import metrics_router
from .middleware import RequestIdMiddleware
from .abuse_controls import AbuseControlsMiddleware
from .tenant import TenantResolutionMiddleware
from .console_routes_auth import router as auth_router
from .console_routes_spend import router as spend_router
from .console_routes_clients import router as clients_router
from .console_routes_pages import router as pages_router
from .console_routes_leads import admin_router as leads_router, public_router
from .console_routes_service_packages_public import public_router as service_packages_public_router
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
from .console_routes_service_packages import admin_router as service_packages_router
from .console_routes_booking_requests import admin_router as booking_requests_router
from .console_routes_payment_intents import admin_router as payment_intents_router
from .console_routes_money_board import admin_router as money_board_router
from .console_routes_qr import router as qr_router
from .console_routes_gov import router as gov_router
from .console_routes_retries import admin_router as retries_router
from .console_routes_integrity import router as integrity_router
from .console_routes_exports import router as exports_router
from .console_routes_events import router as events_router
from .console_routes_alerts import router as alerts_router
from .console_routes_stats import router as stats_router
from .console_routes_bulk import router as bulk_router
from .console_routes_analytics import router as analytics_router
from .console_routes_trade_templates import router as trade_templates_router

from .chat_automation import install_chat_automation_hooks

app = FastAPI(title="Acq Engine Operator Console", version=__version__)  # noqa: F405

# install chat automation hooks (v1)
install_chat_automation_hooks()


# Tenant middleware always added; checks AE_MULTI_TENANT_ENABLED at request time
app.add_middleware(RequestIdMiddleware)
app.add_middleware(TenantResolutionMiddleware)
app.add_middleware(AbuseControlsMiddleware)
app.include_router(health_router)
app.include_router(metrics_router)
# auth + health probes
app.include_router(auth_router)
app.include_router(spend_router)
app.include_router(clients_router)
app.include_router(pages_router)
app.include_router(leads_router)
app.include_router(public_router)
app.include_router(service_packages_public_router)
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
app.include_router(service_packages_router)
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
app.include_router(trade_templates_router)

@app.middleware("http")
async def guardrails_middleware(request: Request, call_next):
    """Public surface guardrails: size caps + rate limits + abuse logging."""
    import datetime as _dt
    from fastapi import Response
    from . import repo as _repo

    path = request.url.path or ""
    ip = request.client.host if request.client else ""
    ip_hint = _coarse_ip_hint(ip)

    # --- size caps ---
    try:
        cl = request.headers.get("content-length")
        if cl is not None and cl.strip().isdigit():
            if int(cl) > _MAX_BODY_BYTES:
                # best-effort abuse log
                try:
                    db_path = _resolve_db(request.query_params.get("db"))
                    _repo.insert_abuse(
                        db_path,
                        ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                        ip_hint=ip_hint,
                        endpoint=path,
                        reason="payload_too_large",
                        meta={"content_length": int(cl), "limit": _MAX_BODY_BYTES},
                    )
                except Exception:
                    pass
                return Response(status_code=413, content="payload too large")
        # If no content-length, read body to enforce cap (and re-inject for downstream)
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if body and len(body) > _MAX_BODY_BYTES:
                try:
                    db_path = _resolve_db(request.query_params.get("db"))
                    _repo.insert_abuse(
                        db_path,
                        ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                        ip_hint=ip_hint,
                        endpoint=path,
                        reason="payload_too_large",
                        meta={"body_bytes": len(body), "limit": _MAX_BODY_BYTES},
                    )
                except Exception:
                    pass
                return Response(status_code=413, content="payload too large")
            # starlette request body is cached in _body
            request._body = body
    except Exception:
        pass

    # --- rate limits ---
    try:
        if ip and ip != "testclient":
            if path == "/lead":
                ok = _rate_limit_check(ip, "lead", limit=_RL_LEAD_PER_HOUR, window_s=3600)
                if not ok:
                    try:
                        db_path = _resolve_db(request.query_params.get("db"))
                        _repo.insert_abuse(
                            db_path,
                            ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                            ip_hint=ip_hint,
                            endpoint=path,
                            reason="rate_limited",
                            meta={"bucket": "lead", "limit_per_hour": _RL_LEAD_PER_HOUR},
                        )
                    except Exception:
                        pass
                    return Response(status_code=429, content="rate limited")
            elif path.startswith("/api/"):
                ok = _rate_limit_check(ip, "api", limit=_RL_API_PER_HOUR, window_s=3600)
                if not ok:
                    try:
                        db_path = _resolve_db(request.query_params.get("db"))
                        _repo.insert_abuse(
                            db_path,
                            ts=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                            ip_hint=ip_hint,
                            endpoint=path,
                            reason="rate_limited",
                            meta={"bucket": "api", "limit_per_hour": _RL_API_PER_HOUR},
                        )
                    except Exception:
                        pass
                    return Response(status_code=429, content="rate limited")
    except Exception:
        pass

    return await call_next(request)


STATIC_DIR = os.path.join(os.path.dirname(__file__), "console_static")
if os.path.isdir(STATIC_DIR):
    app.mount("/console_static", StaticFiles(directory=STATIC_DIR), name="console_static")


@app.get("/api/health")
def health(_: None = Depends(require_role("viewer"))):
    return {"ok": True, "version": __version__}


@app.get("/", response_class=HTMLResponse)
def root_redirect():
    """Redirect root to console."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/console")

@app.get("/console", response_class=HTMLResponse)
def console():
    """Serve console HTML - authentication handled client-side."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse("<h1>console assets missing</h1>", status_code=500)
    return FileResponse(index_path)


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





@app.get("/api/activity")
def activity(
    db: str,
    limit: int = 200,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    _: None = Depends(require_role("viewer")),
):
    items = repo.list_activity(db, limit=limit, action=action, entity_type=entity_type, entity_id=entity_id)
    return {"count": len(items), "items": [a.model_dump() for a in items]}











@app.get("/console/clients")
def console_clients(
    request: Request,
    db_path: str | None = None,
    status: str | None = None,
):
    require_secret(request)
    from . import db as dbmod
    db_path = _resolve_db_path(db_path)
    dbmod.init_db(db_path)
    clients = repo.list_clients(db_path, status=status, limit=500)

    def _esc(v):
        import html
        return html.escape("" if v is None else str(v))

    rows = []
    for c in clients:
        d = c.model_dump() if hasattr(c, "model_dump") else c.dict()
        rows.append(
            "<tr>"
            f"<td class='mono'><b>{_esc(d.get('client_id'))}</b></td>"
            f"<td>{_esc(d.get('client_name'))}</td>"
            f"<td>{_esc(d.get('trade'))}</td>"
            f"<td>{_esc(d.get('geo_country'))}</td>"
            f"<td>{_esc(d.get('geo_city'))}</td>"
            f"<td><span class='pill {d.get('status')}'>{_esc(d.get('status'))}</span></td>"
            "</tr>"
        )
    rows_html = "\n".join(rows) or "<tr><td colspan='6' class='muted'>no clients yet</td></tr>"

    qs_db = request.query_params.get("db_path") or ""
    qs_status = request.query_params.get("status") or ""

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>AE Console — Clients</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; background: #0b0e14; color: #e6e6e6; }}
    a {{ color: #9ad; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .top {{ display:flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
    .muted {{ color: #9aa4b2; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New"; font-size: 12px; }}
    .card {{ border: 1px solid #222a38; border-radius: 12px; padding: 12px; background: #0f1420; }}
    table {{ width:100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border-bottom: 1px solid rgba(255,255,255,0.06); padding: 10px 8px; vertical-align: top; }}
    th {{ text-align:left; font-size: 12px; color: #9aa4b2; }}
    input {{ background: #0b0e14; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 8px 10px; min-width: 160px; }}
    button {{ background: #1b2636; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 9px 12px; cursor:pointer; }}
    button:hover {{ background:#23314a; }}
    .pill {{ display:inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; border:1px solid #222a38; }}
    .pill.live {{ background:#132216; }}
    .pill.paused {{ background:#2a250f; }}
    .pill.archived {{ background:#241218; }}
    .pill.draft {{ background:#1b1b1b; }}
    form {{ display:flex; flex-wrap:wrap; gap: 8px; align-items:end; margin: 12px 0; }}
    label {{ display:flex; flex-direction:column; gap: 4px; font-size: 12px; }}
    code {{ background:#0b0e14; border:1px solid #222a38; padding:2px 6px; border-radius:8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1 style="margin:0;">Clients</h1>
        <div class="muted">Registry / onboarding surface</div>
      </div>
      <div class="muted">
        <a href="/console">Home</a> · <a href="/console/onboarding">Onboarding</a> · <a href="/console/abuse">Abuse</a>
      </div>
    </div>

    <div class="card">
      <form method="get" action="/console/clients">
        <label>db_path<input name="db_path" value="{_esc(qs_db)}" placeholder="(optional)" /></label>
        <label>status<input name="status" value="{_esc(qs_status)}" placeholder="draft|active|paused|archived" /></label>
        <button type="submit">Filter</button>
      </form>

      <div class="muted">API quickstart (requires header <code>X-AE-SECRET</code>)</div>
      <div class="mono">POST /api/clients body: slug=barber-cm, name=Barber CM, industry=barber, geo=chiang mai, primary_phone=+66..., lead_email=owner@...</div>

      <table>
        <thead>
          <tr>
            <th>id</th><th>name</th><th>trade</th><th>country</th><th>city</th><th>status</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)

@app.get("/console/onboarding")
def console_onboarding(
    request: Request,
    db_path: str | None = None,
    client_id: str | None = None,
    msg: str | None = None,
):
    # Requires cookie-based login OR X-AE-SECRET (admin)
    require_secret(request)
    from . import db as dbmod
    db_path = _resolve_db_path(db_path)
    dbmod.init_db(db_path)

    clients = repo.list_clients(db_path, status=None, limit=500)
    if not client_id and clients:
        client_id = clients[0].client_id

    templates = {}
    if client_id:
        templates = repo.ensure_default_onboarding_templates(db_path, client_id)

    def _esc(v):
        import html
        return html.escape("" if v is None else str(v))

    # Build client select options
    opts = []
    for c in clients:
        cid = c.client_id
        sel = " selected" if cid == client_id else ""
        opts.append(f"<option value='{_esc(cid)}'{sel}>{_esc(cid)} — {_esc(c.client_name)}</option>")
    opts_html = "\n".join(opts) or "<option value=''>no clients</option>"

    utm_policy = _esc(templates.get("utm_policy_md", ""))
    naming_policy = _esc(templates.get("naming_policy_md", ""))
    event_map = _esc(templates.get("event_map_md", ""))

    qs_db = request.query_params.get("db_path") or ""
    qs_client = request.query_params.get("client_id") or (client_id or "")

    banner = ""
    if msg:
        banner = f"<div class='banner'>{_esc(msg)}</div>"

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>AE Console — Onboarding</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; background: #0b0e14; color: #e6e6e6; }}
    a {{ color: #9ad; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .top {{ display:flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
    .muted {{ color: #9aa4b2; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New"; font-size: 12px; }}
    .card {{ border: 1px solid #222a38; border-radius: 12px; padding: 12px; background: #0f1420; }}
    input, select, textarea {{ background: #0b0e14; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 8px 10px; width:100%; }}
    textarea {{ min-height: 220px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New"; font-size: 12px; line-height: 1.4; }}
    button {{ background: #1b2636; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 9px 12px; cursor:pointer; }}
    button:hover {{ background:#23314a; }}
    form.row {{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; align-items:end; }}
    label {{ display:flex; flex-direction:column; gap: 4px; font-size: 12px; }}
    .grid {{ display:grid; grid-template-columns: 1fr; gap: 12px; }}
    .banner {{ border:1px solid #2b6; background: rgba(40,220,120,0.08); padding: 10px 12px; border-radius: 10px; margin-top: 12px; }}
    .danger {{ border-color:#b44; background: rgba(220,40,80,0.08); }}
    code {{ background:#0b0e14; border:1px solid #222a38; padding:2px 6px; border-radius:8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1 style="margin:0;">Onboarding Templates</h1>
        <div class="muted">UTM policy · naming policy · event map (per client)</div>
      </div>
      <div class="muted">
        <a href="/console">Home</a> · <a href="/console/clients">Clients</a> · <a href="/console/abuse">Abuse</a>
      </div>
    </div>

    {banner}

    <div class="card" style="margin-top:12px;">
      <form method="get" action="/console/onboarding" class="row">
        <label>db_path<input name="db_path" value="{_esc(qs_db)}" placeholder="(optional)" /></label>
        <label>client_id<select name="client_id">{opts_html}</select></label>
        <button type="submit">Load</button>
      </form>

      <div class="muted" style="margin-top:10px;">Tip: these templates define **your measurement vocabulary**. Keep them consistent so GA4/Meta/Google tell the same story.</div>
    </div>

    <div class="card" style="margin-top:12px;">
      <form method="post" action="/console/onboarding">
        <input type="hidden" name="db_path" value="{_esc(qs_db)}"/>
        <input type="hidden" name="client_id" value="{_esc(client_id or '')}"/>

        <div class="grid">
          <label>UTM policy (markdown)
            <textarea name="utm_policy_md">{utm_policy}</textarea>
          </label>
          <label>Naming policy (markdown)
            <textarea name="naming_policy_md">{naming_policy}</textarea>
          </label>
          <label>Event map (markdown)
            <textarea name="event_map_md">{event_map}</textarea>
          </label>

          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button name="action" value="ensure_defaults" type="submit">Reset missing defaults</button>
            <button name="action" value="save" type="submit">Save all</button>
          </div>

          <div class="muted mono">API: <code>GET /api/onboarding/{{client_id}}</code> · <code>PUT /api/onboarding/{{client_id}}/{{template_key}}</code> (admin)</div>
        </div>
      </form>
    </div>

  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/console/onboarding")
async def console_onboarding_post(request: Request):
    require_secret(request)
    form = await request.form()
    db_path = _resolve_db_path(form.get("db_path"))
    client_id = form.get("client_id") or ""
    action = form.get("action") or "save"

    from . import db as dbmod
    dbmod.init_db(db_path)

    if not client_id:
        return RedirectResponse(url="/console/onboarding?msg=missing_client_id", status_code=303)

    if action == "ensure_defaults":
        repo.ensure_default_onboarding_templates(db_path, client_id)
        url = f"/console/onboarding?db_path={client_id and ''}{''}"
        return RedirectResponse(url=f"/console/onboarding?client_id={client_id}&msg=defaults_ensured", status_code=303)

    # save
    repo.upsert_onboarding_template(db_path, client_id, "utm_policy_md", str(form.get("utm_policy_md") or ""))
    repo.upsert_onboarding_template(db_path, client_id, "naming_policy_md", str(form.get("naming_policy_md") or ""))
    repo.upsert_onboarding_template(db_path, client_id, "event_map_md", str(form.get("event_map_md") or ""))
    return RedirectResponse(url=f"/console/onboarding?client_id={client_id}&msg=saved", status_code=303)

@app.get("/console/abuse")
def console_abuse(
    request: Request,
    db: str | None = None,
    since: str | None = None,
    reason: str | None = None,
    endpoint_prefix: str | None = None,
    limit: int = 200,
):
    """Human-friendly abuse monitor (server-rendered HTML)."""
    require_secret(request)
    db_path = _resolve_db(db)

    data = repo.list_abuse(
        db_path,
        since_ts=since,
        reason=reason,
        endpoint_prefix=endpoint_prefix,
        limit=limit,
    )

    def _esc(s: str | None) -> str:
        import html
        return html.escape("" if s is None else str(s))

    # Render
    rows_html = []
    for r in data.get("recent", []):
        rows_html.append(
            "<tr>"
            f"<td>{_esc(r.get('ts'))}</td>"
            f"<td>{_esc(r.get('ip_hint'))}</td>"
            f"<td>{_esc(r.get('endpoint'))}</td>"
            f"<td>{_esc(r.get('reason'))}</td>"
            f"<td><pre class='mono'>{_esc(r.get('meta'))}</pre></td>"
            "</tr>"
        )
    rows = "\n".join(rows_html) or "<tr><td colspan='5' class='muted'>no data</td></tr>"

    # Summary cards
    def _kv_list(items, k1, k2, max_n=12):
        out=[]
        for it in (items or [])[:max_n]:
            out.append(f"<li><span class='mono'>{_esc(it.get(k1))}</span> <span class='muted'>×</span> <b>{_esc(it.get(k2))}</b></li>")
        return "<ul class='kv'>" + "".join(out) + "</ul>"

    by_reason = _kv_list(data.get("by_reason"), "reason", "count")
    by_endpoint = _kv_list(data.get("by_endpoint"), "endpoint", "count")
    by_ip = _kv_list(data.get("top_ip_hints"), "ip_hint", "count")

    q = request.query_params
    base_params = []
    for key in ["db", "since", "reason", "endpoint_prefix", "limit"]:
        v = q.get(key)
        if v is not None:
            base_params.append(f"{key}={_esc(v)}")
    qp = "&".join(base_params)

    # export link keeps same filters
    export_href = "/api/abuse/export" + ("?" + qp if qp else "")

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>AE Console — Abuse Monitor</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; background: #0b0e14; color: #e6e6e6; }}
    a {{ color: #9ad; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    .top {{ display:flex; justify-content: space-between; align-items: baseline; gap: 12px; }}
    .muted {{ color: #9aa4b2; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New"; font-size: 12px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 16px 0; }}
    .card {{ border: 1px solid #222a38; border-radius: 12px; padding: 12px; background: #0f1420; }}
    .kv {{ list-style:none; padding-left: 0; margin: 8px 0 0; }}
    .kv li {{ display:flex; justify-content: space-between; gap: 8px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }}
    .kv li:last-child {{ border-bottom: none; }}
    form {{ display:flex; flex-wrap:wrap; gap: 8px; align-items: end; margin: 12px 0; }}
    label {{ display:flex; flex-direction:column; gap: 4px; font-size: 12px; }}
    input {{ background: #0b0e14; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 8px 10px; min-width: 160px; }}
    button {{ background: #1b2636; border: 1px solid #222a38; color:#e6e6e6; border-radius: 10px; padding: 9px 12px; cursor:pointer; }}
    button:hover {{ background:#23314a; }}
    table {{ width:100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border-bottom: 1px solid rgba(255,255,255,0.06); padding: 10px 8px; vertical-align: top; }}
    th {{ text-align:left; font-size: 12px; color: #9aa4b2; }}
    pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <h1 style="margin:0;">Abuse Monitor</h1>
        <div class="muted">DB: <span class="mono">{_esc(db_path)}</span></div>
      </div>
      <div class="muted">
        <a href="/">Home</a> · <a href="{export_href}">Export CSV</a>
      </div>
    </div>

    <form method="get" action="/console/abuse">
      <label>db<input name="db" value="{_esc(q.get('db') or '')}" /></label>
      <label>since (ISO ts)<input name="since" value="{_esc(q.get('since') or '')}" placeholder="2026-02-01T00:00:00Z" /></label>
      <label>reason<input name="reason" value="{_esc(q.get('reason') or '')}" placeholder="rate_limited" /></label>
      <label>endpoint_prefix<input name="endpoint_prefix" value="{_esc(q.get('endpoint_prefix') or '')}" placeholder="/api/" /></label>
      <label>limit<input name="limit" value="{_esc(q.get('limit') or '200')}" /></label>
      <button type="submit">Apply</button>
    </form>

    <div class="grid">
      <div class="card">
        <div class="muted">By reason</div>
        {by_reason}
      </div>
      <div class="card">
        <div class="muted">By endpoint</div>
        {by_endpoint}
      </div>
      <div class="card">
        <div class="muted">Top IP hints</div>
        {by_ip}
      </div>
    </div>

    <div class="card">
      <div class="top">
        <div class="muted">Recent events</div>
        <div class="muted mono">rows: {len(data.get('recent', []))}</div>
      </div>
      <table>
        <thead>
          <tr><th>ts</th><th>ip_hint</th><th>endpoint</th><th>reason</th><th>meta</th></tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html, status_code=200)



