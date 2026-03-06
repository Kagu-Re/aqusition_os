from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import db


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def backup_db(
    *,
    db_path: str,
    backup_dir: str = "ops/backups",
    label: str = "",
    keep_last: int = 30,
) -> Dict[str, Any]:
    """Copy SQLite db to ops/backups with checksum + manifest, and prune old backups.

    keep_last: retain N most recent backups (simple + deterministic; avoids time ambiguity).
    """
    src = Path(db_path)
    if not src.exists():
        raise FileNotFoundError(f"db_path not found: {db_path}")

    out_dir = Path(backup_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = _now()
    safe_label = "".join([c for c in (label or "").strip().replace(" ", "_") if c.isalnum() or c in ("_", "-", ".")])[:40]
    stem = f"acq_{ts.strftime('%Y%m%dT%H%M%SZ')}"
    if safe_label:
        stem += f"_{safe_label}"

    dst = out_dir / f"{stem}.db"
    manifest = out_dir / f"{stem}.json"

    shutil.copy2(src, dst)
    sha = _sha256_file(dst)

    meta = {
        "created_utc": _iso(ts),
        "db_src": str(src),
        "db_backup": str(dst),
        "sha256": sha,
        "bytes": int(dst.stat().st_size),
        "label": safe_label,
    }
    manifest.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

    # prune old backups by created time encoded in filename (lexicographic)
    db_files = sorted(out_dir.glob("acq_*.db"), key=lambda p: p.name, reverse=True)
    removed = []
    for p in db_files[keep_last:]:
        try:
            j = p.with_suffix(".json")
            if j.exists():
                j.unlink()
            p.unlink()
            removed.append(p.name)
        except Exception:
            pass

    return {"backup": meta, "pruned": removed}


def restore_db(
    *,
    db_path: str,
    backup_path: str,
    verify_checksum: bool = True,
    prebackup: bool = True,
    backup_dir: str = "ops/backups",
) -> Dict[str, Any]:
    """Restore db from a backup file. Optionally create a pre-restore backup."""
    dst = Path(db_path)
    src = Path(backup_path)

    if not src.exists():
        raise FileNotFoundError(f"backup_path not found: {backup_path}")

    # checksum verify if manifest exists
    manifest = src.with_suffix(".json")
    if verify_checksum and manifest.exists():
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
            expected = str(meta.get("sha256", "")).strip()
            if expected:
                actual = _sha256_file(src)
                if actual != expected:
                    raise RuntimeError(f"checksum mismatch: expected {expected} got {actual}")
        except Exception as e:
            raise RuntimeError(f"checksum verification failed: {e}") from e

    pre = None
    if prebackup and dst.exists():
        pre = backup_db(db_path=str(dst), backup_dir=backup_dir, label="pre_restore", keep_last=30)["backup"]

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    return {
        "restored_to": str(dst),
        "from_backup": str(src),
        "prebackup": pre,
        "bytes": int(dst.stat().st_size),
    }


def ops_health(
    *,
    db_path: str,
    backup_dir: str = "ops/backups",
) -> Dict[str, Any]:
    """Minimal ops health snapshot: db readable, disk usage, last backup, last publish."""
    out: Dict[str, Any] = {"status": "ok", "checks": {}}

    p = Path(db_path)
    out["checks"]["db_path"] = str(p)
    out["checks"]["db_exists"] = p.exists()

    # disk usage at parent dir
    try:
        usage = shutil.disk_usage(str(p.parent if p.parent.exists() else Path(".")))
        out["checks"]["disk"] = {
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": int(usage.free),
            "free_pct": round((usage.free / usage.total) * 100.0, 2) if usage.total else None,
        }
    except Exception as e:
        out["checks"]["disk_error"] = str(e)

    # DB readability and last publish
    if p.exists():
        try:
            con = db.connect(str(p))
            try:
                row = db.fetchone(con, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT 1")
                out["checks"]["db_readable"] = True if row else True
                last_pub = db.fetchone(con, "SELECT MAX(timestamp) AS ts FROM publish_logs")
                out["checks"]["last_publish_utc"] = last_pub["ts"] if last_pub and last_pub["ts"] else None
                last_event = db.fetchone(con, "SELECT MAX(timestamp) AS ts FROM events")
                out["checks"]["last_event_utc"] = last_event["ts"] if last_event and last_event["ts"] else None
            finally:
                con.close()
        except Exception as e:
            out["status"] = "warn"
            out["checks"]["db_readable"] = False
            out["checks"]["db_error"] = str(e)
    else:
        out["status"] = "warn"

    # backups
    bdir = Path(backup_dir)
    if bdir.exists():
        db_files = sorted(bdir.glob("acq_*.db"), key=lambda p: p.name, reverse=True)
        out["checks"]["backup_count"] = len(db_files)
        out["checks"]["latest_backup"] = str(db_files[0]) if db_files else None
        if db_files:
            out["checks"]["latest_backup_mtime_utc"] = _iso(datetime.fromtimestamp(db_files[0].stat().st_mtime, tz=timezone.utc).replace(microsecond=0))
    else:
        out["checks"]["backup_count"] = 0
        out["checks"]["latest_backup"] = None

    return out
