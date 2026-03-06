from __future__ import annotations

from pathlib import Path

from ae.menu_static_pages import render_menu_html, write_menu_page
from ae.models import Menu, MenuSection, MenuItem
from ae.enums import MenuStatus


def test_render_menu_html_contains_items(tmp_path: Path):
    menu = Menu(
        menu_id="m1",
        client_id="c1",
        name="Test Menu",
        language="en",
        currency="THB",
        status=MenuStatus.active,
        meta={},
        created_at="2026-02-05T00:00:00Z",
        updated_at="2026-02-05T00:00:00Z",
    )
    sections = [MenuSection(section_id="s1", menu_id="m1", title="Drinks", sort_order=1)]
    items = [
        MenuItem(item_id="i1", menu_id="m1", section_id="s1", title="Coffee", description="Hot", price=50.0, currency="THB", is_available=True, sort_order=1, meta={}),
        MenuItem(item_id="i2", menu_id="m1", section_id=None, title="Water", description=None, price=10.0, currency="THB", is_available=True, sort_order=0, meta={}),
    ]
    html = render_menu_html(menu, sections, items)
    assert "Test Menu" in html
    assert "Drinks" in html
    assert "Coffee" in html
    assert "Water" in html
    # write file
    out_path = write_menu_page(tmp_path, menu, sections, items)
    p = Path(out_path)
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "Coffee" in content
