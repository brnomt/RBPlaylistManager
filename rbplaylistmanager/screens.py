"""Modal screens (playlist picker, etc.)."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static


def _count_entries(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return 0
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _slugify_playlist_name(raw: str) -> str:
    name = raw.strip()
    if not name:
        return ""
    if not name.lower().endswith(".m3u8"):
        name += ".m3u8"
    # Reject path separators (keep it as a flat file in the playlist dir).
    name = name.replace("/", "_").replace("\\", "_")
    return name


class PlaylistPicker(ModalScreen[Path | None]):
    """Pick, create, or delete a ``.m3u8`` playlist."""

    DEFAULT_CSS = """
    PlaylistPicker {
        align: center middle;
        background: $background 60%;
    }
    PlaylistPicker > Vertical {
        width: 64;
        max-width: 90%;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    PlaylistPicker .picker-title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }
    PlaylistPicker .picker-subtitle {
        color: $text-muted;
        padding-bottom: 1;
    }
    PlaylistPicker ListView {
        height: auto;
        max-height: 18;
        background: transparent;
        border: round $primary 40%;
    }
    PlaylistPicker ListView > ListItem {
        padding: 0 1;
    }
    PlaylistPicker ListView > ListItem.--highlight {
        background: $accent 25%;
    }
    PlaylistPicker Input {
        margin-top: 1;
        background: transparent;
        border: round $primary 40%;
    }
    PlaylistPicker Input:focus {
        border: round $accent;
    }
    PlaylistPicker .picker-hint {
        color: $text-muted;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancelar", show=False),
        Binding("n", "focus_new", "Nueva", show=False),
        Binding("delete", "delete_current", "Borrar", show=False),
        Binding("ctrl+d", "delete_current", "Borrar", show=False),
    ]

    def __init__(self, playlist_dir: Path, current: Path | None) -> None:
        super().__init__()
        self._playlist_dir = playlist_dir
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                f"Playlists en {self._playlist_dir.name}/",
                classes="picker-title",
            )
            yield Static(str(self._playlist_dir), classes="picker-subtitle")
            yield ListView(id="picker-list")
            yield Input(
                placeholder="Nombre para nueva playlist (Enter para crear)…",
                id="picker-input",
            )
            yield Static(
                "Enter elige · N nueva · Supr borra · Esc cancelar",
                classes="picker-hint",
            )

    def on_mount(self) -> None:
        self._refresh_list()
        self.query_one("#picker-list", ListView).focus()

    def _refresh_list(self, prefer: Path | None = None) -> None:
        lv = self.query_one("#picker-list", ListView)
        lv.clear()
        try:
            self._playlist_dir.mkdir(parents=True, exist_ok=True)
            playlists = sorted(self._playlist_dir.glob("*.m3u8"))
        except OSError:
            playlists = []

        if not playlists:
            lv.append(ListItem(Label("(sin playlists — escribe un nombre abajo)")))
            return

        target = prefer or self._current
        target_index = 0
        for i, path in enumerate(playlists):
            is_current = self._current is not None and path == self._current
            marker = "● " if is_current else "  "
            item = ListItem(
                Label(f"{marker}{path.name}  [{_count_entries(path)}]"),
                name=str(path),
            )
            lv.append(item)
            if target is not None and path == target:
                target_index = i
        lv.index = target_index

    @on(ListView.Selected)
    def _select(self, event: ListView.Selected) -> None:
        event.stop()
        item = event.item
        if item is None or not item.name:
            return
        self.dismiss(Path(item.name))

    @on(Input.Submitted, "#picker-input")
    def _create(self, event: Input.Submitted) -> None:
        event.stop()
        name = _slugify_playlist_name(event.value)
        if not name:
            return
        target = self._playlist_dir / name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("\ufeff", encoding="utf-8")
        except OSError:
            return
        self.dismiss(target)

    def action_focus_new(self) -> None:
        self.query_one("#picker-input", Input).focus()

    def action_delete_current(self) -> None:
        lv = self.query_one("#picker-list", ListView)
        item = lv.highlighted_child
        if item is None or not item.name:
            return
        path = Path(item.name)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return
        # Don't dismiss; let the user keep picking. Refresh + keep position.
        self._refresh_list()

    def action_cancel(self) -> None:
        self.dismiss(None)
