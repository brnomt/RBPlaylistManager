"""Folder cover art: Kitty / textual-image preview or emoji fallback."""

from __future__ import annotations

import os
from pathlib import Path

COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".ico", ".webp"}
NAMED_COVERS = ("cover", "folder", "album", "front", "artwork", "AlbumArt")

_image_support: bool | None = None


def probe_image_support() -> bool:
    """True if textual-image is installed (probe before the Textual app runs)."""
    global _image_support
    if _image_support is None:
        try:
            import textual_image.widget  # noqa: F401
            _image_support = True
        except ImportError:
            _image_support = False
    return _image_support


def is_kitty_terminal() -> bool:
    term = os.environ.get("TERM", "")
    return "kitty" in term.lower() or bool(os.environ.get("KITTY_WINDOW_ID"))


def uses_graphic_covers() -> bool:
    """Graphic thumbnail in the side panel (Kitty TGP / Sixel / half-cell)."""
    return probe_image_support()


def folder_tree_icon() -> str:
    """Prefix for directory rows in the tree."""
    if uses_graphic_covers():
        return "▸ "
    return "📁 "


def track_tree_icon() -> str:
    return "♪ "


def fallback_cover_glyph() -> str:
    if is_kitty_terminal() and not uses_graphic_covers():
        return "🖼"
    return "📁"


def find_folder_cover(folder: Path) -> Path | None:
    """First cover image in *folder* (named files, then any image)."""
    if not folder.is_dir():
        return None

    for stem in NAMED_COVERS:
        for ext in COVER_EXTENSIONS:
            candidate = folder / f"{stem}{ext}"
            if candidate.is_file():
                return candidate
            candidate = folder / f"{stem}{ext.upper()}"
            if candidate.is_file():
                return candidate

    try:
        for child in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if child.is_file() and child.suffix.lower() in COVER_EXTENSIONS:
                return child
    except OSError:
        return None
    return None
