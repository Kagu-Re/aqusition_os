from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import db
from .models import Menu, MenuSection, MenuItem
from .enums import MenuStatus


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def upsert_menu(db_path: str, menu: Menu) -> Menu:
    # Ensure timestamps
    created_at = menu.created_at or _now()
    updated_at = _now()
    meta_json = json.dumps(menu.meta or {}, ensure_ascii=False, separators=(",", ":"))
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO menus(menu_id, client_id, name, language, currency, status, meta_json, created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(menu_id) DO UPDATE SET
                       client_id=excluded.client_id,
                       name=excluded.name,
                       language=excluded.language,
                       currency=excluded.currency,
                       status=excluded.status,
                       meta_json=excluded.meta_json,
                       updated_at=excluded.updated_at""",
            (menu.menu_id, menu.client_id, menu.name, menu.language, menu.currency, (menu.status.value if hasattr(menu.status, 'value') else str(menu.status)), meta_json, created_at, updated_at),
        )
        con.commit()
    finally:
        con.close()
    return Menu(
        menu_id=menu.menu_id,
        client_id=menu.client_id,
        name=menu.name,
        language=menu.language,
        currency=menu.currency,
        status=menu.status if isinstance(menu.status, MenuStatus) else MenuStatus((menu.status.value if hasattr(menu.status, 'value') else str(menu.status))),
        meta=menu.meta or {},
        created_at=created_at,
        updated_at=updated_at,
    )


def get_menu(db_path: str, menu_id: str) -> Optional[Menu]:
    con = db.connect(db_path)
    try:
        row = db.fetchone(con, "SELECT * FROM menus WHERE menu_id=?", (menu_id,))
        if not row:
            return None
        return Menu(
            menu_id=row["menu_id"],
            client_id=row["client_id"],
            name=row["name"],
            language=row["language"],
            currency=row["currency"],
            status=MenuStatus(row["status"]),
            meta=json.loads(row["meta_json"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    finally:
        con.close()


def list_menus(db_path: str, *, client_id: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[Menu]:
    sql = "SELECT * FROM menus"
    params: List[Any] = []
    where: List[str] = []
    if client_id:
        where.append("client_id=?")
        params.append(client_id)
    if status:
        where.append("status=?")
        params.append(status)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[Menu] = []
        for r in rows:
            out.append(Menu(
                menu_id=r["menu_id"],
                client_id=r["client_id"],
                name=r["name"],
                language=r["language"],
                currency=r["currency"],
                status=MenuStatus(r["status"]),
                meta=json.loads(r["meta_json"] or "{}"),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            ))
        return out
    finally:
        con.close()


def upsert_menu_section(db_path: str, section: MenuSection) -> MenuSection:
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO menu_sections(section_id, menu_id, title, sort_order)
                   VALUES(?,?,?,?)
                   ON CONFLICT(section_id) DO UPDATE SET
                       menu_id=excluded.menu_id,
                       title=excluded.title,
                       sort_order=excluded.sort_order""",
            (section.section_id, section.menu_id, section.title, section.sort_order),
        )
        con.commit()
    finally:
        con.close()
    return section


def list_menu_sections(db_path: str, menu_id: str) -> List[MenuSection]:
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, "SELECT * FROM menu_sections WHERE menu_id=? ORDER BY sort_order ASC", (menu_id,))
        return [MenuSection(section_id=r["section_id"], menu_id=r["menu_id"], title=r["title"], sort_order=r["sort_order"]) for r in rows]
    finally:
        con.close()


def upsert_menu_item(db_path: str, item: MenuItem) -> MenuItem:
    meta_json = json.dumps(item.meta or {}, ensure_ascii=False, separators=(",", ":"))
    con = db.connect(db_path)
    try:
        con.execute(
            """INSERT INTO menu_items(item_id, menu_id, section_id, title, description, price, currency, is_available, sort_order, meta_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(item_id) DO UPDATE SET
                       menu_id=excluded.menu_id,
                       section_id=excluded.section_id,
                       title=excluded.title,
                       description=excluded.description,
                       price=excluded.price,
                       currency=excluded.currency,
                       is_available=excluded.is_available,
                       sort_order=excluded.sort_order,
                       meta_json=excluded.meta_json""",
            (
                item.item_id,
                item.menu_id,
                item.section_id,
                item.title,
                item.description,
                item.price,
                item.currency,
                1 if item.is_available else 0,
                item.sort_order,
                meta_json,
            ),
        )
        con.commit()
    finally:
        con.close()
    return item


def list_menu_items(db_path: str, menu_id: str, *, section_id: Optional[str] = None) -> List[MenuItem]:
    sql = "SELECT * FROM menu_items WHERE menu_id=?"
    params: List[Any] = [menu_id]
    if section_id:
        sql += " AND section_id=?"
        params.append(section_id)
    sql += " ORDER BY sort_order ASC"
    con = db.connect(db_path)
    try:
        rows = db.fetchall(con, sql, tuple(params))
        out: List[MenuItem] = []
        for r in rows:
            out.append(MenuItem(
                item_id=r["item_id"],
                menu_id=r["menu_id"],
                section_id=r["section_id"],
                title=r["title"],
                description=r["description"],
                price=r["price"],
                currency=r["currency"],
                is_available=bool(r["is_available"]),
                sort_order=r["sort_order"],
                meta=json.loads(r["meta_json"] or "{}"),
            ))
        return out
    finally:
        con.close()
