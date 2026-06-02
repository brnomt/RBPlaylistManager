"""CLI entry point — no paths required; mounts are auto-detected."""

from __future__ import annotations

from rbplaylistmanager.app import RBPlaylistApp


def main() -> None:
    RBPlaylistApp().run()


if __name__ == "__main__":
    main()
