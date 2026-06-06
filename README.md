# RBPlaylistManager

Gestor de playlists **.m3u8** para iPod con **Rockbox**, con interfaz de terminal en dos paneles.

- Tema **Catppuccin Mocha** y fondos **transparentes** (deja ver el fondo del terminal).
- **Montajes automáticos**: escanea `/run/media`, `/media` y `/mnt` (vfat, exfat, ntfs, etc.). Sin argumentos en la línea de comandos.
- Si no hay ningún dispositivo conectado, te lo dice: conéctalo y pulsa `R`.

## Paneles

| Izquierda | Derecha |
|-----------|---------|
| Montajes → carpetas → pistas | Playlist activa del volumen (`.m3u8` en `Playlists/`) |

Al pulsar **Enter** en un montaje, las playlists del panel derecho usan la carpeta `Playlists` (o `Playlist`) de ese volumen.

## Controles

| Tecla | Acción |
|-------|--------|
| `↑` / `↓` | Navegar montajes, carpetas o playlist |
| `Enter` / `Espacio` (carpeta) | Abrir / cerrar carpeta (carga subcarpetas la primera vez) |
| `→` (pista) | Añadir a la playlist activa |
| `←` (carpeta) | Añadir **todas** las pistas de esa carpeta (recursivo) |
| `←` (playlist) | Quitar pista |
| `←` (biblioteca) | Ir al panel playlist |
| `→` (playlist) | Volver a biblioteca |
| `Tab` | Cambiar foco |
| `P` | **Selector de playlists** (elegir / crear / borrar) |
| `R` | Refrescar montajes detectados |
| `Q` | Salir |

### Selector de playlists (`P`)

Abre un modal con todas las `.m3u8` del volumen activo:

| Tecla | Acción |
|-------|--------|
| `↑` / `↓` | Recorrer playlists |
| `Enter` | Activar la resaltada |
| `N` | Saltar al campo "Nueva" para crearla |
| `Supr` / `Ctrl+D` | Borrar la resaltada |
| `Esc` | Cancelar |

Las rutas en `.m3u8` se guardan como en Rockbox: `/<HDD0>/HQ MUSIC/Artista/pista.flac` (UTF-8 con BOM).

Con **Kitty** + `textual-image` + **Pillow**, miniatura de la carpeta a la derecha (`Cover.jpg`, etc.). En otros terminales, bloques de color o emoji 📁.

## Instalación

```bash
cd RBPlaylistManager
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python -m rbplaylistmanager
```

Conecta el iPod antes de arrancar, o pulsa `R` tras montarlo.

Para que se vea el fondo del terminal, usa un emulador con transparencia (Kitty, Alacritty, Ghostty, etc.).

## Estructura

```
RBPlaylistManager/
└── rbplaylistmanager/
    ├── app.py          # UI + bindings
    ├── mounts.py       # detección de volúmenes
    ├── library.py      # árbol de música
    ├── playlist.py     # lectura / escritura .m3u8
    ├── paths.py        # conversión host ↔ Rockbox
    ├── screens.py      # modales (selector de playlist)
    ├── widgets.py      # CoverPreview
    └── artwork.py      # detección de carátulas
```
