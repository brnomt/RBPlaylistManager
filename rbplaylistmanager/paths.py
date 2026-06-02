"""Rockbox path helpers (HDD0-style paths — wired up in a later step)."""

from __future__ import annotations

from pathlib import Path


# Placeholder prefix for Rockbox on iPod Classic internal storage.
ROCKBOX_ROOT_PREFIX = r"\HDD0"


def host_path_to_rockbox(host_path: Path, music_root: Path) -> str:
    """Convert a host filesystem path to a Rockbox playlist line.

    Example: ``/media/ipod/Music/Artist/track.mp3`` → ``\\HDD0\\Music\\Artist\\track.mp3``
    """
    rel = host_path.resolve().relative_to(music_root.resolve())
    parts = [ROCKBOX_ROOT_PREFIX, *rel.parts]
    return "\\".join(parts)


def rockbox_path_to_display(line: str) -> str:
    """Short label for the UI."""
    return line.replace(ROCKBOX_ROOT_PREFIX + "\\", "").replace("\\", " / ")
