"""Folder cover art: Kitty TGP, half-cell, or emoji fallback."""

from __future__ import annotations

import os
from pathlib import Path

COVER_EXTENSIONS = {".jpg", ".jpeg", ".png", ".ico", ".webp"}
NAMED_COVERS = ("cover", "folder", "album", "front", "artwork", "AlbumArt")
SKIP_COVER_NAMES = frozenset(
    {
        "albumartsmall",
        "albumarts_{",
        "thumbs",
        "desktop.ini",
    }
)

_image_support: bool | None = None


def probe_image_support() -> bool:
    """True if textual-image + Pillow are available."""
    global _image_support
    if _image_support is None:
        try:
            import textual_image.widget  # noqa: F401
            from PIL import Image  # noqa: F401

            _image_support = True
        except ImportError:
            _image_support = False
    return _image_support


def is_kitty_terminal() -> bool:
    term = os.environ.get("TERM", "")
    return "kitty" in term.lower() or bool(os.environ.get("KITTY_WINDOW_ID"))


def uses_graphic_covers() -> bool:
    return probe_image_support()


def cover_widget_class():
    """Best Textual image widget for this terminal."""
    from textual_image.widget import HalfcellImage, TGPImage

    if is_kitty_terminal():
        return TGPImage
    return HalfcellImage


def folder_tree_icon() -> str:
    if uses_graphic_covers():
        return "▸ "
    return "📁 "


def track_tree_icon() -> str:
    return "♪ "


def fallback_cover_glyph() -> str:
    return "📁"


def _cover_sort_key(path: Path) -> tuple[int, int]:
    ext = path.suffix.lower()
    ext_rank = {".jpg": 0, ".jpeg": 0, ".png": 1, ".webp": 2, ".ico": 3}.get(ext, 9)
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return ext_rank, -size


def _is_skipped_cover(name: str) -> bool:
    lower = name.lower()
    return any(lower.startswith(skip) for skip in SKIP_COVER_NAMES)


def find_folder_cover(folder: Path) -> Path | None:
    """Best cover image directly inside *folder*."""
    if not folder.is_dir():
        return None

    for stem in NAMED_COVERS:
        for ext in COVER_EXTENSIONS:
            for candidate in (folder / f"{stem}{ext}", folder / f"{stem}{ext.upper()}"):
                if candidate.is_file() and not _is_skipped_cover(candidate.name):
                    return candidate

    try:
        images = [
            child
            for child in folder.iterdir()
            if child.is_file()
            and child.suffix.lower() in COVER_EXTENSIONS
            and not _is_skipped_cover(child.name)
        ]
    except OSError:
        return None

    if not images:
        return None
    return min(images, key=_cover_sort_key)
