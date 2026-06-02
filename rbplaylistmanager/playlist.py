"""Read / write .m3u8 playlist files."""

from __future__ import annotations

from pathlib import Path

from rbplaylistmanager.paths import normalize_playlist_entry

UTF8_BOM = "\ufeff"


def load_playlist(path: Path) -> list[str]:
    """Load playlist entries (one path per non-empty, non-comment line)."""
    if not path.is_file():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(normalize_playlist_entry(line))
    return lines


def save_playlist(path: Path, entries: list[str]) -> None:
    """Write UTF-8 .m3u8 with BOM (Rockbox on iPod expects it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(entries)
    if body:
        body += "\n"
    path.write_text(UTF8_BOM + body, encoding="utf-8")
