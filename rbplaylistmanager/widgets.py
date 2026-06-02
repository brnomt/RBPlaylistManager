"""Extra UI widgets."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from rbplaylistmanager.artwork import (
    cover_widget_class,
    fallback_cover_glyph,
    find_folder_cover,
    uses_graphic_covers,
)


class CoverPreview(Vertical):
    """Folder cover thumbnail (Kitty TGP or half-cell blocks)."""

    DEFAULT_CSS = """
    CoverPreview {
        dock: right;
        width: 18;
        min-width: 18;
        height: 10;
        min-height: 10;
        margin: 0 0 0 1;
        background: $surface 30%;
        border: round $primary 25%;
    }
    CoverPreview Static#cover-emoji {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }
    CoverPreview Image {
        width: 18;
        height: 10;
    }
    """

    def compose(self):
        yield Static(fallback_cover_glyph(), id="cover-emoji")
        if uses_graphic_covers():
            widget_cls = cover_widget_class()
            yield widget_cls(id="cover-img")

    def show_folder(self, folder: Path | None) -> None:
        emoji = self.query_one("#cover-emoji", Static)
        cover = find_folder_cover(folder) if folder else None

        if uses_graphic_covers() and cover is not None:
            image = self.query_one("#cover-img")
            image.image = str(cover)
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
        emoji.update(fallback_cover_glyph() if cover is None else "🖼")
