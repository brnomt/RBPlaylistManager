"""CLI entry point — no paths required; mounts are auto-detected."""

from __future__ import annotations

# Protocol probe must run before Textual starts (textual-image requirement).
try:
    import textual_image.widget  # noqa: F401
except ImportError:
    pass

from rbplaylistmanager.app import RBPlaylistApp


def main() -> None:
    RBPlaylistApp().run()


if __name__ == "__main__":
    main()
