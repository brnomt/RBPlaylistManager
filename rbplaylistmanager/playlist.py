"""Read / write .m3u8 playlist files."""

from __future__ import annotations

from pathlib import Path


def load_playlist(path: Path) -> list[str]:
    """Load playlist entries (one path per non-empty, non-comment line)."""
    if not path.is_file():
        return []
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def save_playlist(path: Path, entries: list[str]) -> None:
    """Write playlist as UTF-8 .m3u8 (Rockbox path conversion applied later)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(entries)
    if body:
        body += "\n"
    path.write_text(body, encoding="utf-8")
