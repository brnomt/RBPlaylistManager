"""Extra UI widgets."""

from __future__ import annotations

from pathlib import Path

from textual.containers import Vertical
from textual.widgets import Static

from rbplaylistmanager.artwork import (
    fallback_cover_glyph,
    find_folder_cover,
    uses_graphic_covers,
)


class CoverPreview(Vertical):
    """Tiny folder cover: textual-image on Kitty, emoji otherwise."""

    DEFAULT_CSS = """
    CoverPreview {
        dock: right;
        width: 14;
        height: 7;
        margin: 0 0 0 1;
        background: transparent;
    }
    CoverPreview Static#cover-emoji {
        width: 100%;
        height: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }
    CoverPreview Image {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self):
        yield Static(fallback_cover_glyph(), id="cover-emoji")
        if uses_graphic_covers():
            from textual_image.widget import Image

            yield Image("", id="cover-img")

    def show_folder(self, folder: Path | None) -> None:
        emoji = self.query_one("#cover-emoji", Static)
        cover = find_folder_cover(folder) if folder else None

        if uses_graphic_covers() and cover is not None:
            image = self.query_one("#cover-img")
            image.image = str(cover)
            image.display = "block"
            emoji.display = "none"
            return

        if uses_graphic_covers():
            try:
                self.query_one("#cover-img").display = "none"
            except Exception:
                pass

        emoji.display = "block"
        emoji.update(fallback_cover_glyph() if cover is None else "🖼")
