"""Terminal GUI: library tree (left) + active playlist (right)."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, Tree
from textual.widgets.tree import TreeNode

from rbplaylistmanager.artwork import folder_tree_icon, track_tree_icon
from rbplaylistmanager.library import (
    NodeData,
    collect_audio_files,
    list_directory,
)
from rbplaylistmanager.mounts import MountInfo, discover_mounts, mount_for_path
from rbplaylistmanager.paths import host_path_to_rockbox, rockbox_path_to_display
from rbplaylistmanager.playlist import load_playlist, save_playlist
from rbplaylistmanager.screens import PlaylistPicker
from rbplaylistmanager.widgets import CoverPreview


class TrackAdded(Message):
    """Emitted after a track is appended to the playlist."""


class TrackRemoved(Message):
    """Emitted after a track is removed from the playlist."""


class LibraryPane(Vertical):
    DEFAULT_CSS = """
    LibraryPane {
        width: 1fr;
        border: round $primary 40%;
        background: transparent;
        min-height: 10;
    }
    LibraryPane Static.title {
        background: $primary 25%;
        color: $foreground;
        padding: 0 1;
        text-style: bold;
    }
    #library-body {
        height: 1fr;
    }
    #library-body Tree {
        width: 1fr;
        height: 1fr;
        background: transparent;
        scrollbar-background: transparent;
        scrollbar-color: $primary 50%;
    }
    """


class PlaylistPane(Vertical):
    DEFAULT_CSS = """
    PlaylistPane {
        width: 1fr;
        border: round $accent 40%;
        background: transparent;
        min-height: 10;
    }
    PlaylistPane Static.title {
        background: $accent 25%;
        color: $foreground;
        padding: 0 1;
        text-style: bold;
    }
    PlaylistPane ListView {
        height: 1fr;
        background: transparent;
        scrollbar-background: transparent;
        scrollbar-color: $accent 50%;
    }
    PlaylistPane ListView > ListItem.--highlight {
        background: $accent 25%;
    }
    """


class RBPlaylistApp(App):
    """Two-pane Rockbox playlist manager."""

    TITLE = "RBPlaylistManager"
    SUB_TITLE = "Rockbox · iPod · .m3u8"
    THEME = "catppuccin-mocha"

    CSS = """
    Screen {
        layout: vertical;
        background: transparent;
    }
    Header {
        background: transparent;
        color: $foreground;
        border-bottom: hkey $primary 35%;
    }
    Footer {
        background: transparent;
        color: $text-muted;
        border-top: hkey $primary 35%;
    }
    Footer > .footer--key {
        background: transparent;
    }
    #main-row {
        height: 1fr;
        background: transparent;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: transparent;
        color: $text-muted;
        padding: 0 1;
    }
    #library-tree:focus {
        border: tall $secondary;
    }
    ListView:focus {
        border: tall $primary;
    }
    #library-tree > .tree--cursor {
        background: $primary 35%;
        color: $foreground;
        text-style: bold;
    }
    #library-tree > .tree--highlight-line {
        background: $primary 15%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("tab", "focus_next", "Panel", show=False),
        Binding("p", "pick_playlist", "Playlist"),
        Binding("r", "refresh_mounts", "Montajes"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._mounts: list[MountInfo] = []
        self._active_mount: MountInfo | None = None
        self._playlist_dir: Path | None = None
        self._playlists: list[Path] = []
        self._playlist_index = 0
        self._entries: list[str] = []

    @property
    def active_playlist(self) -> Path | None:
        if not self._playlists:
            return None
        return self._playlists[self._playlist_index]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-row"):
            with LibraryPane():
                yield Static("Biblioteca", classes="title", id="lib-title")
                with Horizontal(id="library-body"):
                    yield Tree("Montajes", id="library-tree")
                    yield CoverPreview(id="cover-preview")
            with PlaylistPane():
                yield Static("Playlist", classes="title", id="pl-title")
                yield ListView(id="playlist-list")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_mount_list()
        self._init_library_tree()
        self._discover_playlists()
        self._reload_playlist()
        self._refresh_titles()
        tree = self.query_one("#library-tree", Tree)
        tree.auto_expand = False
        tree.focus()
        if not self._mounts:
            self._set_status("Conecta un dispositivo y pulsa R para detectarlo.")

    def action_refresh_mounts(self) -> None:
        self._refresh_mount_list()
        self._init_library_tree()
        if not self._mounts:
            self._set_status("Ningún montaje detectado. Conecta el iPod y reintenta (R).")
        else:
            self._set_status(f"{len(self._mounts)} montaje(s) detectado(s)")

    def _refresh_mount_list(self) -> None:
        self._mounts = discover_mounts()
        if not self._mounts:
            self._active_mount = None
            self._playlist_dir = None
            self._playlists = []
            self._playlist_index = 0
            self._entries = []

    def _init_library_tree(self) -> None:
        tree = self.query_one("#library-tree", Tree)
        tree.clear()
        tree.show_root = True
        tree.root.set_label("Montajes")
        tree.root.allow_expand = True
        tree.root.expand()

        if not self._mounts:
            placeholder = tree.root.add_leaf("(sin montajes — pulsa R)")
            placeholder.allow_expand = False
            self._update_cover_preview(None)
            return

        for mount in self._mounts:
            node = tree.root.add(
                f"💾 {mount.label}",
                data=NodeData(path=mount.path, is_dir=True, is_mount=True),
            )
            node.allow_expand = True

        if tree.root.children:
            first = tree.root.children[0]
            tree.select_node(first)
            self._update_cover_preview(first)

    def _sync_mount_context(self, node: TreeNode | None) -> None:
        if node is None or node.data is None:
            return
        mount = mount_for_path(node.data.path, self._mounts)
        if mount is None and node.data.is_mount:
            mount = next((m for m in self._mounts if m.path == node.data.path), None)
        if mount is None:
            return

        changed = mount.path != (
            self._active_mount.path if self._active_mount else None
        )
        self._active_mount = mount
        playlist_dir = mount.playlists_dir
        try:
            playlist_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        if playlist_dir != self._playlist_dir:
            self._playlist_dir = playlist_dir
            changed = True

        if changed:
            self._discover_playlists()
            self._reload_playlist()

    def _populate_directory_node(self, node: TreeNode) -> None:
        data: NodeData | None = node.data
        if data is None or not data.is_dir or data.populated:
            return

        subdirs, files = list_directory(data.path)
        for subdir in subdirs:
            child = node.add(
                f"{folder_tree_icon()}{subdir.name}",
                data=NodeData(path=subdir, is_dir=True),
            )
            child.allow_expand = True
        for track in files:
            child = node.add(
                f"{track_tree_icon()}{track.name}",
                data=NodeData(path=track, is_dir=False),
            )
            child.allow_expand = False

        data.populated = True
        node.tree.refresh()

    @on(Tree.NodeHighlighted)
    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        """Update preview / status as the cursor moves; don't expand."""
        event.stop()
        self._update_cover_preview(event.node)
        self._refresh_titles()

    def _update_cover_preview(self, node: TreeNode | None) -> None:
        preview = self.query_one("#cover-preview", CoverPreview)
        if node is None or node.data is None:
            preview.show_folder(None)
            return
        data = node.data
        if data.is_dir:
            preview.show_folder(data.path)
        else:
            preview.show_folder(data.path.parent)

    @on(Tree.NodeSelected)
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Enter on the tree: open / close a folder."""
        event.stop()
        self.action_library_enter()

    def action_library_enter(self) -> None:
        """Enter: open folder / mount (lazy-load children and expand)."""
        tree = self.query_one("#library-tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return

        data = node.data
        if not data.is_dir:
            self._set_status("→ en una pista para añadir a la playlist")
            return

        self._sync_mount_context(node)
        if not data.populated:
            self._populate_directory_node(node)
            node.expand()
        elif node.is_expanded:
            node.collapse()
        else:
            node.expand()
        self._refresh_titles()

    def _discover_playlists(self) -> None:
        if self._playlist_dir is None:
            self._playlists = []
            self._playlist_index = 0
            return
        self._playlists = sorted(self._playlist_dir.glob("*.m3u8"))
        if not self._playlists:
            default = self._playlist_dir / "default.m3u8"
            save_playlist(default, [])
            self._playlists = [default]
        self._playlist_index = 0

    def _reload_playlist(self) -> None:
        pl_list = self.query_one("#playlist-list", ListView)
        pl_list.clear()
        playlist = self.active_playlist
        if playlist is None:
            self._entries = []
            return
        self._entries = load_playlist(playlist)
        for entry in self._entries:
            pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
        if self._entries:
            pl_list.index = 0

    def _refresh_titles(self) -> None:
        playlist = self.active_playlist
        pl_name = playlist.name if playlist else "—"
        mount_name = self._active_mount.label if self._active_mount else "—"
        self.query_one("#pl-title", Static).update(
            f"Playlist — {pl_name} ({len(self._entries)} pistas)"
        )

        tree = self.query_one("#library-tree", Tree)
        cursor = tree.cursor_node
        location = "/"
        if cursor and cursor.data and self._active_mount:
            try:
                rel = cursor.data.path.relative_to(self._active_mount.path)
                location = str(rel) if str(rel) != "." else "/"
            except ValueError:
                location = cursor.data.path.name

        self.query_one("#lib-title", Static).update(
            f"Biblioteca — {mount_name} · {len(self._mounts)} montaje(s)"
        )
        self._set_status(f"{mount_name}  ›  {location}")

    def _set_status(self, message: str) -> None:
        self.query_one("#status-bar", Static).update(message)

    def _rockbox_entry(self, file_path: Path) -> str | None:
        if self._active_mount is None:
            return None
        try:
            return host_path_to_rockbox(
                file_path.resolve(), self._active_mount.path
            )
        except ValueError:
            return None

    def _persist_playlist(self) -> None:
        playlist = self.active_playlist
        if playlist is None:
            return
        save_playlist(playlist, self._entries)

    def _cursor_file_path(self) -> Path | None:
        tree = self.query_one("#library-tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None:
            return None
        data: NodeData = node.data
        if data.is_dir:
            return None
        return data.path

    def _cursor_directory_path(self) -> Path | None:
        tree = self.query_one("#library-tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None or not node.data.is_dir:
            return None
        if node is tree.root:
            return None
        return node.data.path

    def _add_folder_to_playlist(self, folder: Path) -> tuple[int, int]:
        """Add all audio under *folder*. Returns ``(added, skipped_duplicates)``."""
        tree = self.query_one("#library-tree", Tree)
        self._sync_mount_context(tree.cursor_node)
        if self._active_mount is None:
            return 0, 0
        tracks = collect_audio_files(folder)
        added = 0
        skipped = 0
        pl_list = self.query_one("#playlist-list", ListView)
        for track in tracks:
            entry = self._rockbox_entry(track)
            if entry is None:
                continue
            if entry in self._entries:
                skipped += 1
                continue
            self._entries.append(entry)
            pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
            added += 1
        if added:
            pl_list.index = len(self._entries) - 1
            self._persist_playlist()
            self._refresh_titles()
        return added, skipped

    def action_pick_playlist(self) -> None:
        """Open the playlist picker."""
        if self._playlist_dir is None or self._active_mount is None:
            self._set_status(
                "Selecciona un montaje primero (Enter sobre un dispositivo)."
            )
            return

        def _picked(chosen: Path | None) -> None:
            # Always re-discover: the picker may have created or deleted files.
            self._discover_playlists()

            if chosen is not None and chosen.exists():
                if chosen not in self._playlists:
                    # Refresh once more in case glob missed it (race).
                    self._discover_playlists()
                try:
                    self._playlist_index = self._playlists.index(chosen)
                except ValueError:
                    self._playlist_index = 0
                self._reload_playlist()
                self._refresh_titles()
                self._set_status(f"Playlist activa: {self.active_playlist.name}")
                return

            # Cancelled or current was deleted while open.
            current = self.active_playlist
            if current is None or not current.exists():
                self._playlist_index = 0
                self._reload_playlist()
                self._refresh_titles()

        self.push_screen(
            PlaylistPicker(self._playlist_dir, self.active_playlist),
            _picked,
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        event.stop()

    def on_key(self, event) -> None:
        lib_tree = self.query_one("#library-tree", Tree)
        pl_list = self.query_one("#playlist-list", ListView)

        if event.key == "space" and lib_tree.has_focus:
            self.action_library_enter()
            event.prevent_default()
            event.stop()
            return

        if event.key == "right" and lib_tree.has_focus:
            file_path = self._cursor_file_path()
            if file_path is None:
                self._set_status("Enter/Espacio abre carpeta · → pista · ← carpeta entera")
                event.prevent_default()
                event.stop()
                return
            if self._active_mount is None:
                self._set_status("Selecciona un montaje primero.")
                event.prevent_default()
                event.stop()
                return
            entry = self._rockbox_entry(file_path)
            if entry is None:
                event.prevent_default()
                event.stop()
                return
            if entry in self._entries:
                self._set_status("Ya está en la playlist.")
                return
            self._entries.append(entry)
            pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
            pl_list.index = len(self._entries) - 1
            self._persist_playlist()
            self._refresh_titles()
            self._set_status(
                f"Añadido → {self.active_playlist.name if self.active_playlist else ''}"
            )
            self.post_message(TrackAdded())
            event.prevent_default()
            event.stop()
            return

        if event.key == "left" and pl_list.has_focus:
            if not self._entries:
                return
            idx = pl_list.index
            if idx is None:
                idx = 0
            removed = self._entries.pop(idx)
            pl_list.clear()
            for entry in self._entries:
                pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
            if self._entries:
                pl_list.index = min(idx, len(self._entries) - 1)
            self._persist_playlist()
            self._refresh_titles()
            self._set_status(f"Eliminado: {rockbox_path_to_display(removed)}")
            self.post_message(TrackRemoved())
            event.prevent_default()
            event.stop()
            return

        if event.key == "left" and lib_tree.has_focus:
            folder = self._cursor_directory_path()
            if folder is not None:
                if self._active_mount is None:
                    self._set_status("Selecciona un montaje primero.")
                    event.prevent_default()
                    event.stop()
                    return
                added, skipped = self._add_folder_to_playlist(folder)
                if added == 0 and skipped == 0:
                    self._set_status("No hay pistas en esta carpeta.")
                elif skipped:
                    self._set_status(
                        f"Añadidas {added} pistas ({skipped} ya estaban en la playlist)"
                    )
                else:
                    self._set_status(
                        f"Añadidas {added} pistas → "
                        f"{self.active_playlist.name if self.active_playlist else ''}"
                    )
                event.prevent_default()
                event.stop()
                return
            pl_list.focus()
            event.prevent_default()
            event.stop()
            return

        if event.key == "right" and pl_list.has_focus:
            lib_tree.focus()
            event.prevent_default()
            event.stop()
