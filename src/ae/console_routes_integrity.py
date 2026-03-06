from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from fastapi import Depends

from .console_support import require_role, _resolve_db
from .integrity_validator import run_integrity_check
from .repo_integrity_reports import get_latest_integrity_report, get_integrity_report

router = APIRouter(prefix="/api/reliability", tags=["reliability"])


@router.get("/integrity/latest")
def integrity_latest(db: str | None = Depends(_resolve_db), _=Depends(require_role("admin"))):
    db_path = db
    rep = get_latest_integrity_report(db_path)
    return rep.model_dump() if rep else {"status": "none"}


@router.get("/integrity/{report_id}")
def integrity_get(report_id: str, db: str | None = Depends(_resolve_db), _=Depends(require_role("admin"))):
    db_path = db
    rep = get_integrity_report(db_path, report_id)
    if not rep:
        return {"error": "not_found", "report_id": report_id}
    return rep.model_dump()


class IntegrityRunRequest(BaseModel):
    emit_events: bool = True


@router.post("/integrity/run")
def integrity_run(body: IntegrityRunRequest, db: str | None = Depends(_resolve_db), _=Depends(require_role("admin"))):
    db_path = db
    rep = run_integrity_check(db_path, emit_events=body.emit_events)
    return rep.model_dump()
