"""Folder tree scanning for the music library."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".wav", ".wma"}

DEMO_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "demo_library"


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


def ensure_demo_library() -> Path:
    """Create a small on-disk tree when no mounts are available."""
    root = DEMO_LIBRARY_DIR
    tracks = {
        "Pink Floyd/The Wall": [
            "01 - In The Flesh.mp3",
            "02 - The Thin Ice.mp3",
        ],
        "Led Zeppelin/IV": [
            "01 - Black Dog.mp3",
            "02 - Rock and Roll.mp3",
        ],
        "Queen/A Night at the Opera": [
            "01 - Death on Two Legs.mp3",
            "02 - Lazing on a Sunday.mp3",
        ],
        "Rush/2112": [
            "01 - 2112 Overture.mp3",
        ],
        "Rush/Moving Pictures": [
            "01 - Tom Sawyer.mp3",
        ],
    }
    for folder, names in tracks.items():
        dir_path = root / folder
        dir_path.mkdir(parents=True, exist_ok=True)
        for name in names:
            file_path = dir_path / name
            if not file_path.exists():
                file_path.write_bytes(b"")
    return root


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
