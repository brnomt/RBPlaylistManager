"""Folder cover art using half-cell rendering (works in Kitty and most terminals)."""

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

_pillow_ok: bool | None = None
_textual_image_ok: bool | None = None

# Preview panel size in terminal cells.
COVER_COLS = 20
COVER_ROWS = 11


def probe_image_support() -> bool:
    """True if we can render cover thumbnails."""
    return _has_pillow() and _has_textual_image()


def _has_pillow() -> bool:
    global _pillow_ok
    if _pillow_ok is None:
        try:
            from PIL import Image  # noqa: F401

            _pillow_ok = True
        except ImportError:
            _pillow_ok = False
    return _pillow_ok


def _has_textual_image() -> bool:
    global _textual_image_ok
    if _textual_image_ok is None:
        try:
            import textual_image.widget  # noqa: F401
            from textual_image.widget import HalfcellImage  # noqa: F401

            _textual_image_ok = True
        except ImportError:
            _textual_image_ok = False
    return _textual_image_ok


def is_kitty_terminal() -> bool:
    term = os.environ.get("TERM", "")
    return "kitty" in term.lower() or bool(os.environ.get("KITTY_WINDOW_ID"))


def uses_graphic_covers() -> bool:
    return probe_image_support()


def cover_widget_class():
    """Half-cell images are reliable inside Textual layouts."""
    from textual_image.widget import HalfcellImage

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


def load_cover_thumbnail(path: Path):
    """PIL image sized for the preview panel (half-cell pixels)."""
    from PIL import Image as PILImage
    from textual_image._terminal import get_cell_size

    cell = get_cell_size()
    max_w = max(COVER_COLS * cell.width, 40)
    max_h = max(COVER_ROWS * cell.height, 40)
    img = PILImage.open(path)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    img.thumbnail((max_w, max_h), PILImage.Resampling.LANCZOS)
    if img.mode == "RGBA":
        background = PILImage.new("RGB", img.size, (30, 30, 46))
        background.paste(img, mask=img.split()[3])
        img = background
    return img
