from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import db
from .models import Client
from .enums import Trade

def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v)

def _log_alert(
    db_path: str,
    *,
    ts: str,
    status: str,
    alert_type: str,
    campaign: str | None,
    metric: str | None,
    value: float | None,
    threshold: float | None,
    message: str,
) -> None:
    """Append an alert log entry with basic dedupe (24h window)."""
    from .db import connect, init_db

    with connect(db_path) as conn:
        # alerts_dedupe: suppress identical alerts (same type/campaign/metric) if one exists within the last 24h and is not resolved
        row = conn.execute(
            "SELECT id, ts, status FROM alerts_log WHERE alert_type=? AND IFNULL(campaign,'')=IFNULL(?, '') AND IFNULL(metric,'')=IFNULL(?, '') AND status!='resolved' ORDER BY id DESC LIMIT 1",
            (alert_type, campaign, metric),
        ).fetchone()
        if row:
            try:
                import datetime as _dt
                last_ts = (row[1] or "").replace("Z", "")
                last_dt = _dt.datetime.fromisoformat(last_ts)
                if (_dt.datetime.utcnow() - last_dt).total_seconds() < 24 * 3600:
                    return None
            except Exception:
                # if parsing fails, fall through and insert
                pass

        conn.execute(
            "INSERT INTO alerts_log(ts,status,alert_type,campaign,metric,value,threshold,message) VALUES(?,?,?,?,?,?,?,?)",
            (ts, status, alert_type, campaign, metric, value, threshold, message),
        )
        conn.commit()

def _now_utc_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _fingerprint_alert(a: dict) -> str:
    return "|".join([
        str(a.get("type") or a.get("alert_type") or ""),
        str(a.get("campaign") or ""),
        str(a.get("metric") or ""),
        str(a.get("threshold") or ""),
    ])

def _should_send(db_path: str, fp: str, *, throttle_seconds: int) -> bool:
    from .db import connect, init_db
    import datetime as _dt
    with connect(db_path) as conn:
        row = conn.execute("SELECT last_sent_ts FROM notify_dedupe WHERE fingerprint = ?", (fp,)).fetchone()
    if not row:
        return True
    try:
        last = _dt.datetime.fromisoformat(row[0].replace("Z",""))
    except Exception:
        return True
    age = (_dt.datetime.utcnow() - last).total_seconds()
    return age >= float(throttle_seconds)

def _mark_sent(db_path: str, fp: str, ts: str) -> None:
    from .db import connect, init_db
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO notify_dedupe(fingerprint,last_sent_ts) VALUES(?,?) ON CONFLICT(fingerprint) DO UPDATE SET last_sent_ts=excluded.last_sent_ts",
            (fp, ts),
        )
        conn.commit()

def _fmt_alert_line(a: dict) -> str:
    camp = a.get("campaign") or "-"
    metric = a.get("metric") or "-"
    v = a.get("value")
    t = a.get("threshold")
    msg = a.get("message") or ""
    action = ""
    recs = a.get("recommendations") or []
    if recs and isinstance(recs, list) and recs[0].get("action"):
        action = recs[0]["action"]
    parts = [
        f"type={a.get('type')}",
        f"campaign={camp}",
        f"metric={metric}",
        f"value={v}",
        f"thr={t}",
    ]
    if action:
        parts.append(f"action={action}")
    if msg:
        parts.append(f"msg={msg}")
    return " | ".join(parts)

def _send_webhook(url: str, payload: dict) -> tuple[bool, str]:
    import json as _json
    import urllib.request as _ur
    try:
        data = _json.dumps(payload).encode("utf-8")
        req = _ur.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
        with _ur.urlopen(req, timeout=10) as resp:
            code = getattr(resp, "status", 200)
        return (200 <= int(code) < 300), f"status={code}"
    except Exception as e:
        return False, str(e)

def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    import json as _json
    import urllib.request as _ur
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    try:
        data = _json.dumps(payload).encode("utf-8")
        req = _ur.Request(url, data=data, headers={"Content-Type":"application/json"}, method="POST")
        with _ur.urlopen(req, timeout=10) as resp:
            code = getattr(resp, "status", 200)
        return (200 <= int(code) < 300), f"status={code}"
    except Exception as e:
        return False, str(e)

def _append_file(path: str, text: str) -> tuple[bool, str]:
    try:
        from pathlib import Path as _Path
        p = _Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
        return True, "ok"
    except Exception as e:
        return False, str(e)

def get_spend_daily_client_id(db_path: str, spend_id: int) -> str | None:
    """Return client_id for a spend record, or None if not found."""
    from .db import connect, init_db
    with connect(db_path) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT client_id FROM ad_spend_daily WHERE spend_id = ?", (int(spend_id),)).fetchone()
        return row[0] if row else None


def delete_spend_daily(db_path: str, spend_id: int) -> None:
    from .db import connect, init_db
    with connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ad_spend_daily WHERE spend_id = ?", (int(spend_id),))
        conn.commit()

def kpi_stats(
    db_path: str,
    *,
    day_from: str | None = None,
    day_to: str | None = None,
    client_id: str | None = None,
) -> dict:
    """Compute minimal KPI stats for a date window (inclusive).
    Uses:
      - leads: lead_intake.ts -> day = substr(ts,1,10)
      - revenue: sum(booking_value) where booking_status in ('booked','paid') and is_spam=0
      - spend: sum(ad_spend_daily.spend_value)
    Note: assumes a single currency.
    When client_id is set, filters lead_intake and ad_spend_daily by client_id.
    """
    from .db import connect, init_db

    def _w(col: str):
        parts = []
        params = []
        if day_from:
            parts.append(f"{col} >= ?")
            params.append(day_from)
        if day_to:
            parts.append(f"{col} <= ?")
            params.append(day_to)
        if client_id:
            parts.append("client_id = ?")
            params.append(client_id)
        return (" WHERE " + " AND ".join(parts)) if parts else "", params

    with connect(db_path) as conn:
        cur = conn.cursor()

        w_leads, p_leads = _w("substr(ts,1,10)")
        w_spend, p_spend = _w("day")

        # leads
        leads_total = cur.execute(f"SELECT COUNT(*) FROM lead_intake{w_leads}", p_leads).fetchone()[0] or 0
        leads_nospam = cur.execute(
            f"SELECT COUNT(*) FROM lead_intake{w_leads}" + (" AND " if w_leads else " WHERE ") + "is_spam = 0",
            p_leads,
        ).fetchone()[0] or 0

        bookings = cur.execute(
            f"SELECT COUNT(*) FROM lead_intake{w_leads}"
            + (" AND " if w_leads else " WHERE ")
            + "is_spam = 0 AND booking_status IN ('booked','paid')",
            p_leads,
        ).fetchone()[0] or 0

        revenue = cur.execute(
            f"SELECT COALESCE(SUM(booking_value),0) FROM lead_intake{w_leads}"
            + (" AND " if w_leads else " WHERE ")
            + "is_spam = 0 AND booking_status IN ('booked','paid')",
            p_leads,
        ).fetchone()[0] or 0.0

        spend = cur.execute(f"SELECT COALESCE(SUM(spend_value),0) FROM ad_spend_daily{w_spend}", p_spend).fetchone()[0] or 0.0

        # daily series
        leads_daily = cur.execute(
            f"SELECT substr(ts,1,10) AS day, COUNT(*) FROM lead_intake{w_leads}"
            + (" AND " if w_leads else " WHERE ")
            + "is_spam = 0 GROUP BY day ORDER BY day ASC",
            p_leads,
        ).fetchall()

        bookings_daily = cur.execute(
            f"SELECT substr(ts,1,10) AS day, COUNT(*) FROM lead_intake{w_leads}"
            + (" AND " if w_leads else " WHERE ")
            + "is_spam = 0 AND booking_status IN ('booked','paid') GROUP BY day ORDER BY day ASC",
            p_leads,
        ).fetchall()

        revenue_daily = cur.execute(
            f"SELECT substr(ts,1,10) AS day, COALESCE(SUM(booking_value),0) FROM lead_intake{w_leads}"
            + (" AND " if w_leads else " WHERE ")
            + "is_spam = 0 AND booking_status IN ('booked','paid') GROUP BY day ORDER BY day ASC",
            p_leads,
        ).fetchall()

        spend_daily = cur.execute(
            f"SELECT day, COALESCE(SUM(spend_value),0) FROM ad_spend_daily{w_spend} GROUP BY day ORDER BY day ASC",
            p_spend,
        ).fetchall()

    def _safe_div(a: float, b: float):
        return (a / b) if b and b > 0 else None

    cpl = _safe_div(float(spend), float(leads_nospam))
    cpb = _safe_div(float(spend), float(bookings))
    booking_rate = _safe_div(float(bookings), float(leads_nospam))
    aov = _safe_div(float(revenue), float(bookings))
    roas = _safe_div(float(revenue), float(spend))

    def _series(rows, key_name, val_name):
        return [{"day": r[0], val_name: float(r[1] or 0.0)} for r in rows]

    return {
        "window": {"day_from": day_from, "day_to": day_to},
        "totals": {
            "leads_total": int(leads_total),
            "leads_nospam": int(leads_nospam),
            "bookings": int(bookings),
            "revenue": float(revenue),
            "spend": float(spend),
            "roas": roas,
            "cpl": cpl,
            "cpb": cpb,
            "booking_rate": booking_rate,
            "aov": aov,
        },
        "series": {
            "leads_nospam": _series(leads_daily, "day", "count"),
            "bookings": _series(bookings_daily, "day", "count"),
            "revenue": _series(revenue_daily, "day", "value"),
            "spend": _series(spend_daily, "day", "value"),
        },
    }

def campaign_stats(
    db_path: str,
    *,
    day_from: str | None = None,
    day_to: str | None = None,
    min_spend: float = 0.0,
    sort_by: str = "roas",
    client_id: str | None = None,
) -> dict:
    """Campaign-level scorecard keyed by utm_campaign.
    Joins revenue/bookings from `lead_intake` with spend from `ad_spend_daily`.

    Time window (optional):
      - leads/revenue use lead_intake.ts day = substr(ts,1,10)
      - spend uses ad_spend_daily.day

    Returns:
      { window, campaigns: [...], totals }
    """
    from .db import connect, init_db

    def _w(col: str):
        parts = []
        params = []
        if day_from:
            parts.append(f"{col} >= ?")
            params.append(day_from)
        if day_to:
            parts.append(f"{col} <= ?")
            params.append(day_to)
        if client_id:
            parts.append("client_id = ?")
            params.append(client_id)
        return (" WHERE " + " AND ".join(parts)) if parts else "", params

    w_leads, p_leads = _w("substr(ts,1,10)")
    w_spend, p_spend = _w("day")

    with connect(db_path) as conn:
        cur = conn.cursor()

        # revenue/bookings/leads by campaign
        leads_rows = cur.execute(
            f"""
            SELECT COALESCE(utm_campaign,'') AS campaign,
                   COUNT(*) AS leads_nospam,
                   SUM(CASE WHEN booking_status IN ('booked','paid') THEN 1 ELSE 0 END) AS bookings,
                   SUM(CASE WHEN booking_status IN ('booked','paid') THEN COALESCE(booking_value,0) ELSE 0 END) AS revenue
            FROM lead_intake
            {w_leads}
            {(" AND " if w_leads else " WHERE ")} is_spam = 0
            GROUP BY COALESCE(utm_campaign,'')
            ORDER BY campaign ASC
            """,
            p_leads,
        ).fetchall()

        spend_rows = cur.execute(
            f"""
            SELECT COALESCE(utm_campaign,'') AS campaign,
                   COALESCE(SUM(spend_value),0) AS spend
            FROM ad_spend_daily
            {w_spend}
            GROUP BY COALESCE(utm_campaign,'')
            ORDER BY campaign ASC
            """,
            p_spend,
        ).fetchall()

    leads_map = {r[0]: {"campaign": r[0], "leads": int(r[1] or 0), "bookings": int(r[2] or 0), "revenue": float(r[3] or 0.0)} for r in leads_rows}
    spend_map = {r[0]: float(r[1] or 0.0) for r in spend_rows}

    # union keys
    keys = set(leads_map.keys()) | set(spend_map.keys())
    campaigns = []
    for k in sorted(keys):
        base = leads_map.get(k, {"campaign": k, "leads": 0, "bookings": 0, "revenue": 0.0})
        spend = float(spend_map.get(k, 0.0))
        leads = int(base["leads"])
        bookings = int(base["bookings"])
        revenue = float(base["revenue"])

        roas = (revenue / spend) if spend > 0 else None
        cpl = (spend / leads) if leads > 0 else None
        cpb = (spend / bookings) if bookings > 0 else None
        booking_rate = (bookings / leads) if leads > 0 else None
        aov = (revenue / bookings) if bookings > 0 else None

        # simple status rules (v1)
        status = "no_data"
        if spend > 0 and revenue == 0:
            status = "test_failed"
        elif roas is not None:
            if roas >= 3:
                status = "scale"
            elif roas >= 1:
                status = "hold"
            else:
                status = "cut"
        elif leads > 0 and spend == 0:
            status = "organic"

        item = {
            "campaign": k,
            "leads": leads,
            "bookings": bookings,
            "revenue": revenue,
            "spend": spend,
            "roas": roas,
            "cpl": cpl,
            "cpb": cpb,
            "booking_rate": booking_rate,
            "aov": aov,
            "status": status,
        }
        if spend >= float(min_spend or 0.0):
            campaigns.append(item)

    # sort
    def _sort_key(x):
        v = x.get(sort_by)
        if v is None:
            return -1e30
        return float(v)

    campaigns.sort(key=_sort_key, reverse=True)

    totals = {
        "revenue": sum(float(x["revenue"]) for x in campaigns),
        "spend": sum(float(x["spend"]) for x in campaigns),
        "leads": sum(int(x["leads"]) for x in campaigns),
        "bookings": sum(int(x["bookings"]) for x in campaigns),
    }
    totals["roas"] = (totals["revenue"] / totals["spend"]) if totals["spend"] > 0 else None

    return {"window": {"day_from": day_from, "day_to": day_to}, "totals": totals, "campaigns": campaigns}

def simulate_budget(
    db_path: str,
    *,
    campaign: str,
    delta_spend: float,
    mode: str = "roas_const",
    day_from: str | None = None,
    day_to: str | None = None,
    client_id: str | None = None,
) -> dict:
    """Simple what-if simulator for adding spend to a campaign.

    Modes:
      - roas_const: keep ROAS constant -> projected_revenue_add = delta_spend * roas
      - cpl_const: keep CPL constant -> projected_leads_add = delta_spend / cpl
      - cpb_const: keep CPBooking constant -> projected_bookings_add = delta_spend / cpb

    Uses current campaign stats as baseline (from campaign_stats()).
    """
    snap = campaign_stats(db_path, day_from=day_from, day_to=day_to, min_spend=0.0, sort_by="roas", client_id=client_id)
    items = snap.get("campaigns", [])
    cur = None
    for it in items:
        if (it.get("campaign") or "") == (campaign or ""):
            cur = it
            break
    if cur is None:
        raise ValueError(f"campaign not found: {campaign!r}")

    delta_spend = float(delta_spend or 0.0)
    if delta_spend < 0:
        raise ValueError("delta_spend must be >= 0")

    base = {
        "campaign": campaign,
        "leads": int(cur.get("leads") or 0),
        "bookings": int(cur.get("bookings") or 0),
        "revenue": float(cur.get("revenue") or 0.0),
        "spend": float(cur.get("spend") or 0.0),
        "roas": cur.get("roas"),
        "cpl": cur.get("cpl"),
        "cpb": cur.get("cpb"),
        "booking_rate": cur.get("booking_rate"),
        "aov": cur.get("aov"),
        "status": cur.get("status"),
    }

    proj = {
        "delta_spend": delta_spend,
        "mode": mode,
        "delta_leads": None,
        "delta_bookings": None,
        "delta_revenue": None,
        "assumptions": {},
    }

    # helpers
    roas = base["roas"]
    cpl = base["cpl"]
    cpb = base["cpb"]
    br = base["booking_rate"]
    aov = base["aov"]

    if mode == "roas_const":
        if roas is None:
            raise ValueError("cannot roas_const: roas is null")
        proj["delta_revenue"] = float(delta_spend) * float(roas)
        proj["assumptions"] = {"roas_const": float(roas)}
        # derive bookings/leads if possible
        if aov and aov > 0:
            proj["delta_bookings"] = float(proj["delta_revenue"]) / float(aov)
        if br and br > 0 and proj["delta_bookings"] is not None:
            proj["delta_leads"] = float(proj["delta_bookings"]) / float(br)

    elif mode == "cpl_const":
        if cpl is None or cpl <= 0:
            raise ValueError("cannot cpl_const: cpl is null/<=0")
        proj["delta_leads"] = float(delta_spend) / float(cpl)
        proj["assumptions"] = {"cpl_const": float(cpl)}
        if br and br > 0:
            proj["delta_bookings"] = float(proj["delta_leads"]) * float(br)
        if aov and aov > 0 and proj["delta_bookings"] is not None:
            proj["delta_revenue"] = float(proj["delta_bookings"]) * float(aov)

    elif mode == "cpb_const":
        if cpb is None or cpb <= 0:
            raise ValueError("cannot cpb_const: cpb is null/<=0")
        proj["delta_bookings"] = float(delta_spend) / float(cpb)
        proj["assumptions"] = {"cpb_const": float(cpb)}
        if aov and aov > 0:
            proj["delta_revenue"] = float(proj["delta_bookings"]) * float(aov)
        if br and br > 0:
            # derive leads from booking_rate
            proj["delta_leads"] = float(proj["delta_bookings"]) / float(br)

    else:
        raise ValueError(f"unknown mode: {mode}")

    # totals projection
    projected = {
        "spend": base["spend"] + delta_spend,
        "revenue": base["revenue"] + (proj["delta_revenue"] or 0.0),
        "leads": base["leads"] + int(round(proj["delta_leads"])) if proj["delta_leads"] is not None else None,
        "bookings": base["bookings"] + int(round(proj["delta_bookings"])) if proj["delta_bookings"] is not None else None,
    }
    projected["roas"] = (projected["revenue"] / projected["spend"]) if projected["spend"] > 0 else None

    return {
        "window": snap.get("window"),
        "baseline": base,
        "projection": proj,
        "projected_totals": projected,
    }


# ---------------------------
# Alerts / thresholds (v1)
# ---------------------------

DEFAULT_THRESHOLDS = {
    "min_roas": 1.5,
    "max_cpl": 300.0,
    "min_booking_rate": 0.05,
    "max_spend_no_revenue": 1000.0,
}

def get_thresholds(db_path: str) -> dict:
    """Return thresholds dict. Missing keys fall back to defaults."""
    from .db import connect, init_db
    with connect(db_path) as conn:
        rows = conn.execute("SELECT k, v FROM alert_thresholds").fetchall()
    out = dict(DEFAULT_THRESHOLDS)
    for k, v in rows:
        try:
            out[k] = float(v) if k != "note" else v
        except Exception:
            out[k] = v
    return out

def set_thresholds(db_path: str, patch: dict) -> dict:
    """Upsert thresholds. Accepts numeric fields as int/float/str."""
    from .db import connect, init_db
    clean = {}
    for k, v in (patch or {}).items():
        if k not in DEFAULT_THRESHOLDS:
            continue
        if v is None:
            continue
        if isinstance(v, (int, float)):
            clean[k] = float(v)
        else:
            clean[k] = float(str(v).strip())
    with connect(db_path) as conn:
        cur = conn.cursor()
        for k, v in clean.items():
            cur.execute("INSERT INTO alert_thresholds(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
        conn.commit()
    return get_thresholds(db_path)

def list_alerts(db_path: str, *, status: str | None = None, limit: int = 200) -> dict:
    """List latest alerts."""
    from .db import connect, init_db
    q = "SELECT id, ts, status, alert_type, campaign, metric, value, threshold, message, ack_ts, ack_by, resolved_ts, note FROM alerts_log"
    params = []
    if status:
        q += " WHERE status = ?"
        params.append(status)
    q += " ORDER BY id DESC LIMIT ?"
    params.append(int(limit))
    with connect(db_path) as conn:
        rows = conn.execute(q, params).fetchall()
    alerts = []
    for r in rows:
        alerts.append({
            "id": r[0],
            "ts": r[1],
            "status": r[2],
            "type": r[3],
            "campaign": r[4],
            "metric": r[5],
            "value": r[6],
            "threshold": r[7],
            "message": r[8],
            "ack_ts": r[9],
            "ack_by": r[10],
            "resolved_ts": r[11],
            "note": r[12],
            "recommendations": recommend_playbook({
                "type": r[3], "metric": r[5],
            }),
        })
    return {"alerts": alerts}

def evaluate_alerts(

    db_path: str,
    *,
    day_from: str | None = None,
    day_to: str | None = None,
) -> dict:
    """Evaluate KPI + campaign thresholds and append alerts_log entries."""
    import datetime as _dt
    ts = _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    thr = get_thresholds(db_path)

    # KPI-level
    kpis = kpi_stats(db_path, day_from=day_from, day_to=day_to)
    totals = kpis.get("totals", {})
    created = 0
    created_alerts = []

    roas = totals.get("roas")
    if roas is not None and roas < thr["min_roas"]:
        _log_alert(
            db_path,
            ts=ts,
            status="open",
            alert_type="kpi_below_threshold",
            campaign=None,
            metric="roas",
            value=float(roas),
            threshold=float(thr["min_roas"]),
            message=f"ROAS {roas:.2f} < min_roas {thr['min_roas']:.2f}",
        )
        created_alerts.append({"ts": ts, "type": "kpi_below_threshold", "campaign": None, "metric": "roas", "value": float(roas), "threshold": float(thr["min_roas"]), "message": f"ROAS {roas:.2f} < min_roas {thr['min_roas']:.2f}", "recommendations": recommend_playbook({"type":"kpi_below_threshold","metric":"roas"})})
        created += 1

    cpl = totals.get("cpl")
    if cpl is not None and cpl > thr["max_cpl"]:
        _log_alert(
            db_path,
            ts=ts,
            status="open",
            alert_type="kpi_above_threshold",
            campaign=None,
            metric="cpl",
            value=float(cpl),
            threshold=float(thr["max_cpl"]),
            message=f"CPL {cpl:.2f} > max_cpl {thr['max_cpl']:.2f}",
        )
        created_alerts.append({"ts": ts, "type": "kpi_above_threshold", "campaign": None, "metric": "cpl", "value": float(cpl), "threshold": float(thr["max_cpl"]), "message": f"CPL {cpl:.2f} > max_cpl {thr['max_cpl']:.2f}", "recommendations": recommend_playbook({"type":"kpi_above_threshold","metric":"cpl"})})
        created += 1

    br = totals.get("booking_rate")
    if br is not None and br < thr["min_booking_rate"]:
        _log_alert(
            db_path,
            ts=ts,
            status="open",
            alert_type="kpi_below_threshold",
            campaign=None,
            metric="booking_rate",
            value=float(br),
            threshold=float(thr["min_booking_rate"]),
            message=f"Booking rate {br:.3f} < min_booking_rate {thr['min_booking_rate']:.3f}",
        )
        created_alerts.append({"ts": ts, "type": "kpi_below_threshold", "campaign": None, "metric": "booking_rate", "value": float(br), "threshold": float(thr["min_booking_rate"]), "message": f"Booking rate {br:.3f} < min_booking_rate {thr['min_booking_rate']:.3f}", "recommendations": recommend_playbook({"type":"kpi_below_threshold","metric":"booking_rate"})})
        created += 1

    # Campaign-level: spend but no revenue (test_failed) above spend threshold
    camps = campaign_stats(db_path, day_from=day_from, day_to=day_to, min_spend=0.0, sort_by="spend").get("campaigns", [])
    for c in camps:
        spend = float(c.get("spend") or 0.0)
        revenue = float(c.get("revenue") or 0.0)
        if spend >= thr["max_spend_no_revenue"] and revenue == 0.0:
            camp = c.get("campaign") or ""
            _log_alert(
                db_path,
                ts=ts,
                status="open",
                alert_type="campaign_spend_no_revenue",
                campaign=camp,
                metric="spend",
                value=spend,
                threshold=float(thr["max_spend_no_revenue"]),
                message=f"Campaign {camp!r} spend {spend:.0f} with revenue=0 (>= {thr['max_spend_no_revenue']:.0f})",
            )
            created_alerts.append({"ts": ts, "type": "campaign_spend_no_revenue", "campaign": camp, "metric": "spend", "value": spend, "threshold": float(thr["max_spend_no_revenue"]), "message": f"Campaign {camp!r} spend {spend:.0f} with revenue=0 (>= {thr['max_spend_no_revenue']:.0f})", "recommendations": recommend_playbook({"type":"campaign_spend_no_revenue","metric":"spend"})})
            created += 1

    return {
        "window": {"day_from": day_from, "day_to": day_to},
        "thresholds": thr,
        "created": created,
        "created_alerts": created_alerts,
        "kpis": totals,
    }


# ---------------------------
# Playbooks (v1)
# ---------------------------

PLAYBOOKS = {
    "kpi_below_threshold:roas": [
        {"action": "tighten targeting", "why": "low ROAS indicates poor match or weak offer"},
        {"action": "pause worst campaigns", "why": "stop the bleeding, reallocate budget"},
        {"action": "fix tracking sanity", "why": "validate spend/revenue mapping and UTM consistency"},
        {"action": "improve landing + CTA", "why": "raise conversion rate before scaling spend"},
    ],
    "kpi_above_threshold:cpl": [
        {"action": "narrow audience", "why": "reduce low-intent clicks"},
        {"action": "refresh creatives", "why": "fight ad fatigue and improve CTR"},
        {"action": "raise qualification friction", "why": "filter out low-value leads (price anchors, requirements)"},
    ],
    "kpi_below_threshold:booking_rate": [
        {"action": "audit lead quality", "why": "booking rate drop often means mismatch or weak follow-up"},
        {"action": "reduce form friction", "why": "ensure qualified leads can book quickly"},
        {"action": "script follow-up SOP", "why": "tight response times increase bookings"},
    ],
    "campaign_spend_no_revenue:spend": [
        {"action": "pause campaign", "why": "spend with zero revenue beyond threshold = failed test"},
        {"action": "check conversion event wiring", "why": "ensure booking event fires and is recorded"},
        {"action": "verify offer + landing", "why": "ensure the promise matches the page"},
    ],
}

def list_playbooks() -> dict:
    """Return all playbooks."""
    return {"playbooks": PLAYBOOKS}

def recommend_playbook(alert: dict) -> list[dict]:
    """Return recommended actions for an alert dict (from alerts_log)."""
    a_type = (alert or {}).get("type") or (alert or {}).get("alert_type") or ""
    metric = (alert or {}).get("metric") or ""
    key = f"{a_type}:{metric}"
    return PLAYBOOKS.get(key, PLAYBOOKS.get(a_type, []))


# ---------------------------
# Notifier (v1)
# ---------------------------

DEFAULT_NOTIFY_CONFIG = {
    # Telegram Bot API
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    # Generic webhook (POST JSON)
    "webhook_url": "",
    # Local fallback log file path
    "file_path": "ops/notify.log",
    # Throttle window (seconds)
    "throttle_seconds": 86400,
}

def get_notify_config(db_path: str) -> dict:
    from .db import connect, init_db
    with connect(db_path) as conn:
        rows = conn.execute("SELECT k, v FROM notify_config").fetchall()
    out = dict(DEFAULT_NOTIFY_CONFIG)
    for k, v in rows:
        if k == "throttle_seconds":
            try:
                out[k] = int(float(v))
            except Exception:
                out[k] = DEFAULT_NOTIFY_CONFIG["throttle_seconds"]
        else:
            out[k] = v
    return out

def set_notify_config(db_path: str, patch: dict) -> dict:
    from .db import connect, init_db
    clean = {}
    for k, v in (patch or {}).items():
        if k not in DEFAULT_NOTIFY_CONFIG:
            continue
        if v is None:
            continue
        if k == "throttle_seconds":
            clean[k] = str(int(float(v)))
        else:
            clean[k] = str(v)
    with connect(db_path) as conn:
        cur = conn.cursor()
        for k, v in clean.items():
            cur.execute("INSERT INTO notify_config(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
        conn.commit()
    return get_notify_config(db_path)

def notify_alerts(db_path: str, alerts: list[dict], *, cfg: dict | None = None) -> dict:
    """Send notifications for alerts with throttle/dedupe. Returns delivery report."""
    cfg = cfg or get_notify_config(db_path)
    throttle = int(cfg.get("throttle_seconds") or DEFAULT_NOTIFY_CONFIG["throttle_seconds"])
    ts = _now_utc_iso()

    sent = 0
    skipped = 0
    errors = []

    lines = []
    for a in alerts or []:
        fp = _fingerprint_alert(a)
        if not _should_send(db_path, fp, throttle_seconds=throttle):
            skipped += 1
            continue
        line = _fmt_alert_line(a)
        lines.append(line)
        _mark_sent(db_path, fp, ts)
        sent += 1

    if not lines:
        return {"sent": 0, "skipped": skipped, "channels": {}, "errors": []}

    text = "AE ALERTS\n" + "\n".join(f"- {ln}" for ln in lines)
    channels = {}

    # Telegram
    token = (cfg.get("telegram_bot_token") or "").strip()
    chat_id = (cfg.get("telegram_chat_id") or "").strip()
    if token and chat_id:
        ok, info = _send_telegram(token, chat_id, text)
        channels["telegram"] = {"ok": ok, "info": info}
        if not ok:
            errors.append({"channel":"telegram","info":info})

    # Webhook
    wh = (cfg.get("webhook_url") or "").strip()
    if wh:
        ok, info = _send_webhook(wh, {"ts": ts, "alerts": alerts, "text": text})
        channels["webhook"] = {"ok": ok, "info": info}
        if not ok:
            errors.append({"channel":"webhook","info":info})

    # File fallback always (cheap audit)
    fp = (cfg.get("file_path") or DEFAULT_NOTIFY_CONFIG["file_path"]).strip()
    ok, info = _append_file(fp, f"[{ts}]\n{text}\n")
    channels["file"] = {"ok": ok, "info": info}
    if not ok:
        errors.append({"channel":"file","info":info})

    return {"sent": sent, "skipped": skipped, "channels": channels, "errors": errors}

def test_notify(db_path: str) -> dict:
    cfg = get_notify_config(db_path)
    a = {
        "type": "test_notification",
        "campaign": "test",
        "metric": "ping",
        "value": 1,
        "threshold": 0,
        "message": "this is a test alert",
        "recommendations": [{"action":"do nothing","why":"test"}],
    }
    return notify_alerts(db_path, [a], cfg=cfg)

def ack_alert(db_path: str, alert_id: int, *, ack_by: str = "operator", note: str = "") -> dict:
    """Mark alert as acknowledged (status=ack)."""
    from .db import connect, init_db
    ts = _now_utc_iso()
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE alerts_log SET status=?, ack_ts=COALESCE(ack_ts, ?), ack_by=COALESCE(ack_by, ?), note=? WHERE id=?",
            ("ack", ts, ack_by, note, int(alert_id)),
        )
        conn.commit()
    return {"id": int(alert_id), "status": "ack", "ack_ts": ts, "ack_by": ack_by, "note": note}

def resolve_alert(db_path: str, alert_id: int, *, ack_by: str = "operator", note: str = "") -> dict:
    """Mark alert as resolved (status=resolved)."""
    from .db import connect, init_db
    ts = _now_utc_iso()
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE alerts_log SET status=?, resolved_ts=?, ack_by=COALESCE(ack_by, ?), note=? WHERE id=?",
            ("resolved", ts, ack_by, note, int(alert_id)),
        )
        conn.commit()
    return {"id": int(alert_id), "status": "resolved", "resolved_ts": ts, "ack_by": ack_by, "note": note}

def list_clients(db_path: str, status: str | None = None, limit: int = 200) -> list[Client]:
    """List clients from the `clients` table."""
    con = db.connect(db_path)
    try:
        where = ""
        params: list = []
        if status:
            where = "WHERE status=?"
            params.append(status)
        limit = max(1, min(int(limit), 2000))
        rows = db.fetchall(
            con,
            f"SELECT * FROM clients {where} ORDER BY rowid DESC LIMIT ?",
            (*params, limit),
        )
        out: list[Client] = []
        for r in rows:
            d = dict(r)
            d["service_area"] = json.loads(d.pop("service_area_json", "[]"))
            d["license_badges"] = json.loads(d.pop("license_badges_json", "[]"))
            d["service_config_json"] = json.loads(d.pop("service_config_json", "{}"))
            # Handle missing business_model for existing records (default to quote_based)
            if "business_model" not in d or not d["business_model"]:
                d["business_model"] = "quote_based"
            out.append(Client(**d))
        return out
    finally:
        con.close()

