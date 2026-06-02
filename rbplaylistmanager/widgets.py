"""Extra UI widgets."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from rbplaylistmanager.artwork import (
    COVER_COLS,
    COVER_ROWS,
    cover_widget_class,
    fallback_cover_glyph,
    find_folder_cover,
    load_cover_thumbnail,
    uses_graphic_covers,
)


class CoverPreview(Vertical):
    """Folder cover thumbnail (half-cell, visible in Kitty and most terminals)."""

    DEFAULT_CSS = f"""
    CoverPreview {{
        dock: right;
        width: {COVER_COLS};
        min-width: {COVER_COLS};
        height: {COVER_ROWS};
        min-height: {COVER_ROWS};
        margin: 0 0 0 1;
        background: $surface 40%;
        border: round $primary 30%;
    }}
    CoverPreview Static#cover-emoji {{
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }}
    CoverPreview Image {{
        width: {COVER_COLS};
        height: {COVER_ROWS};
    }}
    """

    def compose(self):
        yield Static(fallback_cover_glyph(), id="cover-emoji")
        if uses_graphic_covers():
            yield cover_widget_class()(id="cover-img")

    def show_folder(self, folder: Path | None) -> None:
        emoji = self.query_one("#cover-emoji", Static)
        cover_path = find_folder_cover(folder) if folder else None

        if uses_graphic_covers() and cover_path is not None:
            try:
                thumb = load_cover_thumbnail(cover_path)
            except OSError:
                thumb = None
            if thumb is not None:
                image = self.query_one("#cover-img")
                image.image = thumb
                image.display = "block"
                emoji.display = "none"
                image.refresh(layout=True)
                return

        if uses_graphic_covers():
            try:
                img = self.query_one("#cover-img")
                img.display = "none"
                img.refresh(layout=True)
            except Exception:
                pass

        emoji.display = "block"
        emoji.update(fallback_cover_glyph() if cover_path is None else "🖼")
