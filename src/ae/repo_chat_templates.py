
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .db import connect, init_db
from .models import ChatTemplate


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def upsert_template(db_path: str, tpl: ChatTemplate) -> ChatTemplate:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO chat_templates(template_key, language, body, status, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(template_key) DO UPDATE SET
                    language=excluded.language,
                    body=excluded.body,
                    status=excluded.status,
                    updated_at=excluded.updated_at""",
            (tpl.template_key, tpl.language, tpl.body, tpl.status, _iso(tpl.updated_at)),
        )
        con.commit()
    finally:
        con.close()
    return get_template(db_path, tpl.template_key)  # type: ignore


def get_template(db_path: str, template_key: str) -> Optional[ChatTemplate]:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """SELECT template_key, language, body, status, updated_at
               FROM chat_templates WHERE template_key=?""",
            (template_key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ChatTemplate(
            template_key=row[0],
            language=row[1],
            body=row[2],
            status=row[3],
            updated_at=datetime.fromisoformat(row[4]),
        )
    finally:
        con.close()


def list_templates(db_path: str, *, limit: int = 200) -> List[ChatTemplate]:
    init_db(db_path)
    con = connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """SELECT template_key, language, body, status, updated_at
               FROM chat_templates ORDER BY updated_at DESC LIMIT ?""",
            (int(limit),),
        )
        rows = cur.fetchall()
        return [
            ChatTemplate(
                template_key=r[0],
                language=r[1],
                body=r[2],
                status=r[3],
                updated_at=datetime.fromisoformat(r[4]),
            )
            for r in rows
        ]
    finally:
        con.close()
