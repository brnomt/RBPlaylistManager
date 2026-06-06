"""Folder tree scanning for the music library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".wav", ".wma"}


@dataclass
class NodeData:
    """Data attached to each tree node."""

    path: Path
    is_dir: bool
    populated: bool = False
    is_mount: bool = False


def list_directory(path: Path) -> tuple[list[Path], list[Path]]:
    """Return ``(subdirectories, audio files)`` directly under *path*, sorted by name."""
    if not path.is_dir():
        return [], []

    subdirs: list[Path] = []
    files: list[Path] = []
    try:
        children = list(path.iterdir())
    except OSError:
        return [], []

    for child in sorted(children, key=lambda p: p.name.lower()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            subdirs.append(child)
        elif child.is_file() and child.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(child)
    return subdirs, files


def collect_audio_files(folder: Path) -> list[Path]:
    """All audio files under *folder* (recursive), sorted."""
    if not folder.is_dir():
        return []
    found: list[Path] = []
    try:
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(path)
    except OSError:
        return []
    return sorted(found, key=lambda p: str(p).lower())


def resolve_music_root(file_or_dir: Path, mount_music_root: Path) -> Path:
    """Best ``Music`` root for Rockbox path conversion."""
    music = mount_music_root
    if music.is_dir():
        try:
            file_or_dir.resolve().relative_to(music.resolve())
            return music.resolve()
        except ValueError:
            pass
    return mount_music_root.resolve()
