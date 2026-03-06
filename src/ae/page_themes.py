"""Theme registry for landing page template styles."""

from __future__ import annotations

PAGE_THEMES = {"minimal", "spa", "dark"}
DEFAULT_THEME = "minimal"


def get_theme(style: str | None) -> str:
    """Return validated theme, or default if invalid."""
    return style if style in PAGE_THEMES else DEFAULT_THEME
