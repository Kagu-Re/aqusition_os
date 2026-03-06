from __future__ import annotations

def _build_adapter_override(args) -> dict | None:
    d = {}
    if getattr(args, 'content_adapter', None):
        d['content'] = args.content_adapter
    if getattr(args, 'publisher_adapter', None):
        d['publisher'] = args.publisher_adapter
    if getattr(args, 'analytics_adapter', None):
        d['analytics'] = args.analytics_adapter
    if getattr(args, 'publish_out_dir', None):
        d['publish_out_dir'] = args.publish_out_dir
    if getattr(args, 'framer_out_dir', None):
        d['framer_out_dir'] = args.framer_out_dir
    if getattr(args, 'static_out_dir', None):
        d['static_out_dir'] = args.static_out_dir
    return d or None

import json
import hashlib
import re
from pathlib import Path
from typing import Optional, List




def _compute_preflight_report(work_queue_path: str, patch_queue_path: str, *, stale_days: int) -> dict:
    """Compute queue integrity report used by `preflight` and optional work-start gate."""
    from .workqueue import backfill_client_ids
    from .workqueue_reader import read_work_queue
    from .metrics import stale_work, bottleneck_flags
    from .timeutils import now_utc_iso

    backfill = backfill_client_ids(work_queue_path, patch_queue_path)
    rows = read_work_queue(work_queue_path)

    missing_client = [r for r in rows if (r.client_id or "").strip() == ""]
    bad_status = [r for r in rows if r.status.lower() not in ("open", "doing", "blocked", "done")]
    blocked = [r for r in rows if r.status.lower() == "blocked"]
    blocked_no_reason = [r for r in blocked if "BLOCKED:" not in (r.notes or "")]
    stale = stale_work(rows, days=stale_days)

    actionable = []
    for r in missing_client:
        actionable.append({"issue": "missing_client_id", "work_id": r.work_id, "patch_id": r.patch_id})
    for r in bad_status:
        actionable.append({"issue": "bad_status", "work_id": r.work_id, "patch_id": r.patch_id, "status": r.status})
    for r in blocked_no_reason:
        actionable.append({"issue": "blocked_no_reason", "work_id": r.work_id, "patch_id": r.patch_id})
    for s in stale:
        actionable.append({"issue": "stale", "work_id": s.work_id, "patch_id": s.patch_id, "client_id": s.client_id, "age_days": s.age_days})

    now_utc = now_utc_iso()

    return {
        "backfill": backfill,
        "counts": {
            "total": len(rows),
            "missing_client_id": len(missing_client),
            "bad_status": len(bad_status),
            "blocked_no_reason": len(blocked_no_reason),
            "stale_days": stale_days,
            "stale": len(stale),
            "actionable": len(actionable),
        },
        "warnings": bottleneck_flags(rows, now_utc=now_utc),
        "actionable": actionable,
    }


def _read_env(env_path: str = "ops/ENV.json") -> str:
    """Return environment name (dev/staging/prod). Defaults to 'dev' if missing/invalid."""
    try:
        v = json.loads(Path(env_path).read_text(encoding="utf-8"))
        env = str(v.get("environment", "dev")).strip().lower()
        return env if env else "dev"
    except Exception:
        return "dev"


def _load_sla_policy(path: str) -> dict:
    defaults = {"open_sla_days": 14, "doing_sla_days": 7, "block_on_breach": False}
    data = _load_json(path)
    if not isinstance(data, dict):
        return defaults
    out = dict(defaults)
    for k in defaults:
        if k in data:
            out[k] = data[k]
    # normalize
    try:
        out["open_sla_days"] = int(out["open_sla_days"])
    except Exception:
        out["open_sla_days"] = defaults["open_sla_days"]
    try:
        out["doing_sla_days"] = int(out["doing_sla_days"])
    except Exception:
        out["doing_sla_days"] = defaults["doing_sla_days"]
    out["block_on_breach"] = bool(out.get("block_on_breach", False))
    return out

def _load_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_preflight_policy(
    *,
    work_queue_path: str,
    patch_queue_path: str,
    stale_days: int,
    max_actionable: int,
    policy_path: str,
    env_path: str,
    profiles_path: str,
) -> dict:
    """Resolve effective policy with precedence:

    CLI flags > ENV profile > policy file > defaults.
    """
    defaults = {
        "stale_days": 7,
        "max_actionable": 0,
        "max_open_total": 50,
        "max_doing_total": 10,
        "max_doing_per_assignee": 3,
        "max_open_per_client": 10,
    }

    policy = _load_json(policy_path)
    env = _read_env(env_path)
    profiles = _load_json(profiles_path)
    prof = profiles.get(env, {}) if isinstance(profiles, dict) else {}

    eff = dict(defaults)

    if isinstance(policy, dict):
        for k in defaults.keys():
            if k in policy:
                eff[k] = policy[k]

    if isinstance(prof, dict):
        for k in defaults.keys():
            if k in prof:
                eff[k] = prof[k]

    # CLI overrides apply only when caller changed from the signature defaults.
    if stale_days != defaults["stale_days"]:
        eff["stale_days"] = stale_days
    if max_actionable != defaults["max_actionable"]:
        eff["max_actionable"] = max_actionable

    # normalize types
    for k in defaults.keys():
        try:
            eff[k] = int(eff[k])
        except Exception:
            eff[k] = defaults[k]

    return {
        "environment": env,
        "effective": eff,
        "sources": {
            "defaults": defaults,
            "policy_path": policy_path,
            "profiles_path": profiles_path,
            "env_path": env_path,
        },
    }

__all__ = ['_build_adapter_override', '_compute_preflight_report', '_read_env', '_load_sla_policy', '_load_json', '_resolve_preflight_policy']
