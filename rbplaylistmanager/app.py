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
    ensure_demo_library,
    list_directory,
)
from rbplaylistmanager.mounts import MountInfo, discover_mounts, mount_for_path
from rbplaylistmanager.paths import host_path_to_rockbox, rockbox_path_to_display
from rbplaylistmanager.playlist import load_playlist, save_playlist
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
    """


class RBPlaylistApp(App):
    """Two-pane Rockbox playlist manager."""

    TITLE = "RBPlaylistManager"
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
    ListView > ListItem.--highlight {
        background: $primary 20%;
    }
    Tree > TreeNode.--highlight {
        background: $primary 15%;
        color: $foreground;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Salir"),
        Binding("tab", "focus_next", "Panel", show=False),
        Binding("p", "cycle_playlist", "Playlist"),
        Binding("r", "refresh_mounts", "Montajes"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._mounts: list[MountInfo] = []
        self._active_mount: MountInfo | None = None
        self._music_root: Path = Path(".")
        self._playlist_dir: Path = Path.cwd() / "playlists"
        self._playlist_dir.mkdir(parents=True, exist_ok=True)
        self._playlists: list[Path] = []
        self._playlist_index = 0
        self._entries: list[str] = []

    @property
    def active_playlist(self) -> Path:
        if not self._playlists:
            return self._playlist_dir / "default.m3u8"
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

    def action_refresh_mounts(self) -> None:
        self._refresh_mount_list()
        self._init_library_tree()
        self._set_status(f"{len(self._mounts)} montaje(s) detectado(s)")

    def _refresh_mount_list(self) -> None:
        self._mounts = discover_mounts()
        if not self._mounts:
            demo = ensure_demo_library()
            self._mounts = [
                MountInfo(path=demo, label="Demo (conecta un iPod)", fstype="demo"),
            ]

    def _init_library_tree(self) -> None:
        tree = self.query_one("#library-tree", Tree)
        tree.clear()
        tree.show_root = True
        tree.root.set_label("Montajes")
        tree.root.allow_expand = True
        tree.root.expand()

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
        self._music_root = mount.music_root
        playlist_dir = mount.playlists_dir
        playlist_dir.mkdir(parents=True, exist_ok=True)

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
        """Actualiza estado y miniatura; no expande carpetas."""
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
        """Enter en el árbol: abrir o cerrar carpeta."""
        event.stop()
        self.action_library_enter()

    def action_library_enter(self) -> None:
        """Enter: abrir carpeta / montaje (cargar hijos y expandir)."""
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
        self._playlists = sorted(self._playlist_dir.glob("*.m3u8"))
        if not self._playlists:
            default = self._playlist_dir / "default.m3u8"
            save_playlist(default, [])
            self._playlists = [default]
        self._playlist_index = 0

    def _reload_playlist(self) -> None:
        self._entries = load_playlist(self.active_playlist)
        pl_list = self.query_one("#playlist-list", ListView)
        pl_list.clear()
        for entry in self._entries:
            pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
        if self._entries:
            pl_list.index = 0

    def _refresh_titles(self) -> None:
        pl_name = self.active_playlist.name
        mount_name = self._active_mount.label if self._active_mount else "—"
        self.query_one("#pl-title", Static).update(
            f"Playlist — {pl_name} ({len(self._entries)} pistas)"
        )
        tree = self.query_one("#library-tree", Tree)
        cursor = tree.cursor_node
        if cursor and cursor.data:
            try:
                rel = cursor.data.path.relative_to(
                    self._active_mount.path if self._active_mount else cursor.data.path
                )
                location = str(rel) if str(rel) != "." else "/"
            except ValueError:
                location = cursor.data.path.name
        else:
            location = "/"
        self.query_one("#lib-title", Static).update(
            f"Biblioteca — {mount_name} · {len(self._mounts)} montaje(s)"
        )
        self._set_status(f"{mount_name}  ›  {location}")

    def _set_status(self, message: str) -> None:
        self.query_one("#status-bar", Static).update(message)

    def _rockbox_entry(self, file_path: Path) -> str:
        device_root = (
            self._active_mount.path if self._active_mount else self._music_root
        )
        return host_path_to_rockbox(file_path.resolve(), device_root)

    def _persist_playlist(self) -> None:
        save_playlist(self.active_playlist, self._entries)

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
        """Add all audio under *folder*. Returns (added, skipped_duplicates)."""
        self._sync_mount_context_for_path(folder)
        tracks = collect_audio_files(folder)
        added = 0
        skipped = 0
        pl_list = self.query_one("#playlist-list", ListView)
        for track in tracks:
            entry = self._rockbox_entry(track)
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

    def _sync_mount_context_for_path(self, path: Path) -> None:
        tree = self.query_one("#library-tree", Tree)
        node = tree.cursor_node
        self._sync_mount_context(node)

    def action_cycle_playlist(self) -> None:
        if len(self._playlists) < 2:
            self._set_status("Solo hay una playlist en esta carpeta.")
            return
        self._playlist_index = (self._playlist_index + 1) % len(self._playlists)
        self._reload_playlist()
        self._refresh_titles()
        self._set_status(f"Playlist activa: {self.active_playlist.name}")

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
                self._set_status("Enter/Espacio abre · → pista · ← carpeta entera")
                event.prevent_default()
                event.stop()
                return
            entry = self._rockbox_entry(file_path)
            if entry in self._entries:
                self._set_status("Ya está en la playlist.")
                return
            self._entries.append(entry)
            pl_list.append(ListItem(Label(rockbox_path_to_display(entry))))
            pl_list.index = len(self._entries) - 1
            self._persist_playlist()
            self._refresh_titles()
            self._set_status(f"Añadido → {self.active_playlist.name}")
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
                added, skipped = self._add_folder_to_playlist(folder)
                if added == 0 and skipped == 0:
                    self._set_status("No hay pistas en esta carpeta.")
                elif skipped:
                    self._set_status(
                        f"Añadidas {added} pistas ({skipped} ya estaban en la playlist)"
                    )
                else:
                    self._set_status(f"Añadidas {added} pistas → {self.active_playlist.name}")
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
