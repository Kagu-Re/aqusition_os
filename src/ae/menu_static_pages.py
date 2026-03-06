from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .models import Menu, MenuSection, MenuItem


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_menu_html(menu: Menu, sections: List[MenuSection], items: List[MenuItem]) -> str:
    """Render a simple, self-contained HTML page for a menu.

    v1 goals:
    - readable on mobile
    - deterministic output (stable ordering)
    - no external assets required
    """
    sections_sorted = sorted(sections, key=lambda s: (s.sort_order, s.section_id))
    items_sorted = sorted(items, key=lambda it: (it.sort_order, it.item_id))

    # Group items by section_id (None items go to a pseudo section)
    by_section: dict[str, list[MenuItem]] = {}
    for it in items_sorted:
        sid = it.section_id or "_unsectioned"
        by_section.setdefault(sid, []).append(it)

    def fmt_price(it: MenuItem) -> str:
        if it.price is None:
            return ""
        cur = it.currency or menu.currency
        return f"{it.price:g} {cur}"

    title = _escape(menu.name)
    lang = _escape(menu.language or "en")

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append(f'<html lang="{lang}">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append(f"<title>{title}</title>")
    # Minimal inline CSS for mobile readability
    parts.append(
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#0b0b0b;color:#f2f2f2;}"
        "header{padding:20px 16px;border-bottom:1px solid #222;background:#0f0f0f;position:sticky;top:0;}"
        "h1{margin:0;font-size:20px;letter-spacing:.2px;}"
        ".meta{opacity:.75;margin-top:6px;font-size:12px;}"
        "main{padding:16px;max-width:820px;margin:0 auto;}"
        ".section{margin:18px 0 22px 0;}"
        ".section h2{margin:0 0 10px 0;font-size:16px;border-left:3px solid #444;padding-left:10px;}"
        ".item{padding:12px 12px;border:1px solid #1f1f1f;border-radius:12px;margin:10px 0;background:#111;}"
        ".row{display:flex;gap:10px;align-items:flex-start;justify-content:space-between;}"
        ".name{font-weight:650;font-size:14px;}"
        ".price{font-weight:650;font-size:13px;white-space:nowrap;opacity:.95;}"
        ".desc{margin-top:6px;opacity:.82;font-size:12px;line-height:1.35;}"
        ".badge{display:inline-block;margin-left:8px;font-size:11px;padding:2px 6px;border:1px solid #333;border-radius:999px;opacity:.8;}"
        "footer{padding:20px 16px;border-top:1px solid #222;opacity:.75;font-size:12px;text-align:center;}"
        "</style>"
    )
    parts.append("</head>")
    parts.append("<body>")
    parts.append("<header>")
    parts.append(f"<h1>{title}</h1>")
    parts.append(f'<div class="meta">Currency: {_escape(menu.currency)} • Status: {_escape(menu.status.value)}</div>')
    parts.append("</header>")
    parts.append("<main>")

    # Unsectioned first if any
    if "_unsectioned" in by_section:
        parts.append('<div class="section">')
        parts.append("<h2>Menu</h2>")
        for it in by_section["_unsectioned"]:
            if not it.is_available:
                continue
            nm = _escape(it.title)
            pr = _escape(fmt_price(it))
            parts.append('<div class="item">')
            parts.append('<div class="row">')
            parts.append(f'<div class="name">{nm}</div>')
            if pr:
                parts.append(f'<div class="price">{pr}</div>')
            parts.append("</div>")
            if it.description:
                parts.append(f'<div class="desc">{_escape(it.description)}</div>')
            parts.append("</div>")
        parts.append("</div>")

    for sec in sections_sorted:
        sec_items = by_section.get(sec.section_id, [])
        # skip empty sections
        if not any(i.is_available for i in sec_items):
            continue
        parts.append('<div class="section">')
        parts.append(f"<h2>{_escape(sec.title)}</h2>")
        for it in sec_items:
            if not it.is_available:
                continue
            nm = _escape(it.title)
            pr = _escape(fmt_price(it))
            parts.append('<div class="item">')
            parts.append('<div class="row">')
            parts.append(f'<div class="name">{nm}</div>')
            if pr:
                parts.append(f'<div class="price">{pr}</div>')
            parts.append("</div>")
            if it.description:
                parts.append(f'<div class="desc">{_escape(it.description)}</div>')
            parts.append("</div>")
        parts.append("</div>")

    parts.append("</main>")
    parts.append("<footer>")
    parts.append("Powered by AE Menu Generator")
    parts.append("</footer>")
    parts.append("</body></html>")
    return "\n".join(parts)


def write_menu_page(output_dir: str | Path, menu: Menu, sections: List[MenuSection], items: List[MenuItem]) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    filename = f"menu-{menu.menu_id}.html"
    html = render_menu_html(menu, sections, items)
    path = out / filename
    path.write_text(html, encoding="utf-8")
    return str(path)
