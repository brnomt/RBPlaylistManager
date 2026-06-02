"""Detect removable / user media mounts (iPod, SD, etc.)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Typical filesystems for iPods, USB sticks, SD cards.
REMOVABLE_FS_TYPES = frozenset(
    {
        "vfat",
        "exfat",
        "ntfs",
        "fuseblk",
        "msdos",
        "hfsplus",
        "hfs",
        "udf",
    }
)

# Where desktop Linux usually mounts external volumes.
SCAN_ROOTS = (
    Path("/run/media"),
    Path("/media"),
    Path("/mnt"),
)

# Skip known non-device mount names under /mnt or /media.
MUSIC_DIR_NAMES = ("Music", "MUSIC", "HQ MUSIC", "music")

IGNORE_MOUNT_NAMES = frozenset(
    {
        "windows",
        "cdrom",
        "floppy",
    }
)


@dataclass(frozen=True, slots=True)
class MountInfo:
    """A mounted volume the user can browse."""

    path: Path
    label: str
    fstype: str

    @property
    def music_root(self) -> Path:
        for name in MUSIC_DIR_NAMES:
            candidate = self.path / name
            if candidate.is_dir():
                return candidate
        return self.path

    @property
    def playlists_dir(self) -> Path:
        for name in ("Playlists", "Playlist", "playlists"):
            candidate = self.path / name
            if candidate.is_dir():
                return candidate
        return self.path / "Playlists"


def _readable_dir(path: Path) -> bool:
    try:
        return path.is_dir() and os.access(path, os.R_OK | os.X_OK)
    except OSError:
        return False


def _mount_label(path: Path, device: str = "") -> str:
    if device:
        base = Path(device).name
        if base and base not in (".", ".."):
            return f"{path.name} ({base})"
    return path.name


def _under_scan_roots(mountpoint: Path) -> bool:
    mp = mountpoint.resolve()
    for root in SCAN_ROOTS:
        try:
            mp.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _from_proc_mounts(seen: set[Path]) -> list[MountInfo]:
    found: list[MountInfo] = []
    proc = Path("/proc/mounts")
    if not proc.is_file():
        return found

    for line in proc.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        device, mountpoint_str, fstype = parts[0], parts[1], parts[2]
        mountpoint = Path(mountpoint_str)
        if fstype not in REMOVABLE_FS_TYPES:
            continue
        if mountpoint.name.lower() in IGNORE_MOUNT_NAMES:
            continue
        if not _under_scan_roots(mountpoint) and mountpoint.parent.name not in ("media", "mnt"):
            # Still allow direct /run/media/user/volume
            if not str(mountpoint).startswith("/run/media/"):
                continue
        try:
            resolved = mountpoint.resolve()
        except OSError:
            continue
        if resolved in seen or not _readable_dir(resolved):
            continue
        seen.add(resolved)
        found.append(
            MountInfo(
                path=resolved,
                label=_mount_label(resolved, device),
                fstype=fstype,
            )
        )
    return found


def _walk_scan_roots(seen: set[Path]) -> list[MountInfo]:
    """Pick up mount points by walking common directories (udisks layout)."""
    found: list[MountInfo] = []
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        try:
            for dirpath, dirnames, _ in os.walk(root, topdown=True):
                # Do not descend into hidden dirs.
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                current = Path(dirpath)
                if current in seen or not _readable_dir(current):
                    continue
                # Leaf-ish: has Music/Playlists or is 2+ levels under /run/media
                rel_depth = len(current.parts) - len(root.parts)
                has_rockbox_layout = (current / "Music").is_dir() or (current / "Playlists").is_dir()
                is_media_leaf = rel_depth >= 2 and root == Path("/run/media")
                is_mnt_leaf = root == Path("/mnt") and rel_depth >= 1
                is_media_sub = root == Path("/media") and rel_depth >= 2
                if has_rockbox_layout or is_media_leaf or is_mnt_leaf or is_media_sub:
                    if current.name.lower() in IGNORE_MOUNT_NAMES:
                        continue
                    seen.add(current)
                    found.append(
                        MountInfo(
                            path=current,
                            label=_mount_label(current),
                            fstype="",
                        )
                    )
                    dirnames.clear()  # don't walk inside a volume root
        except OSError:
            continue
    return found


def discover_mounts() -> list[MountInfo]:
    """Return mounted volumes, newest / deepest paths first, deduplicated."""
    seen: set[Path] = set()
    mounts = _from_proc_mounts(seen)
    mounts.extend(_walk_scan_roots(seen))
    # Prefer deeper path when one mount is parent of another.
    mounts.sort(key=lambda m: (len(m.path.parts), str(m.path).lower()))
    unique: list[MountInfo] = []
    for mount in mounts:
        if any(mount.path != other.path and mount.path.is_relative_to(other.path) for other in unique):
            continue
        if mount.path not in {m.path for m in unique}:
            unique.append(mount)
    unique.sort(key=lambda m: m.label.lower())
    return unique


def mount_for_path(path: Path, mounts: list[MountInfo]) -> MountInfo | None:
    """Find which mount contains *path*."""
    resolved = path.resolve()
    best: MountInfo | None = None
    best_len = -1
    for mount in mounts:
        try:
            resolved.relative_to(mount.path)
        except ValueError:
            continue
        plen = len(mount.path.parts)
        if plen > best_len:
            best = mount
            best_len = plen
    return best
