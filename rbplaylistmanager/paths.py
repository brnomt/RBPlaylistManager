"""Rockbox playlist paths (iPod Classic / HDD0 volume)."""

from __future__ import annotations

from pathlib import Path

# As in playlists created by Rockbox on this device: /<HDD0>/HQ MUSIC/...
VOLUME_PREFIX = "/<HDD0>"


def host_path_to_rockbox(host_path: Path, device_root: Path) -> str:
    """Host file → Rockbox line, e.g. ``/<HDD0>/HQ MUSIC/Artist/track.flac``."""
    rel = host_path.resolve().relative_to(device_root.resolve())
    return VOLUME_PREFIX + "/" + "/".join(rel.parts)


def rockbox_path_to_display(line: str) -> str:
    """Short label for the UI."""
    text = line.strip().lstrip("\ufeff")
    if text.startswith(VOLUME_PREFIX + "/"):
        text = text[len(VOLUME_PREFIX) + 1 :]
    elif text.startswith(VOLUME_PREFIX):
        text = text[len(VOLUME_PREFIX) :].lstrip("/\\")
    return text.replace("\\", " / ").replace("/", " / ")


def normalize_playlist_entry(line: str) -> str:
    """Convert legacy ``\\HDD0\\...`` lines to ``/<HDD0>/...``."""
    text = line.strip().lstrip("\ufeff").replace("\\", "/")
    if text.startswith(VOLUME_PREFIX):
        return text
    idx = text.find("HDD0")
    if idx != -1:
        rest = text[idx + 4 :].lstrip("/")
        if rest:
            return f"{VOLUME_PREFIX}/{rest}"
    return line.strip().lstrip("\ufeff")
