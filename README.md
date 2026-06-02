# RBPlaylistManager

Gestor de playlists **.m3u8** para iPod con **Rockbox**, con interfaz de terminal en dos paneles.

- Tema **Catppuccin Mocha** y fondos **transparentes** (deja ver el fondo del terminal).
- **Montajes automáticos**: escanea `/run/media`, `/media` y `/mnt` (vfat, exfat, ntfs, etc.). Sin argumentos en la línea de comandos.
- Si no hay ningún dispositivo conectado, usa `demo_library/` de ejemplo.

## Paneles

| Izquierda | Derecha |
|-----------|---------|
| Montajes → carpetas → pistas | Playlist activa del volumen (`.m3u8` en `Playlists/`) |

Al pulsar **Enter** en un montaje, las playlists del panel derecho usan la carpeta `Playlists` (o `Playlist`) de ese volumen.

## Controles

| Tecla | Acción |
|-------|--------|
| `↑` / `↓` | Navegar montajes, carpetas o playlist |
| `Enter` (carpeta) | Abrir / cerrar carpeta (carga subcarpetas la primera vez) |
| `→` (pista) | Añadir a la playlist activa |
| `←` (playlist) | Quitar pista |
| `←` (biblioteca) | Ir al panel playlist |
| `→` (playlist) | Volver a biblioteca |
| `Tab` | Cambiar foco |
| `P` | Cambiar playlist `.m3u8` |
| `R` | Refrescar montajes detectados |
| `Q` | Salir |

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
├── rbplaylistmanager/
│   ├── app.py
│   ├── mounts.py       # detección de volúmenes
│   ├── library.py
│   ├── playlist.py
│   └── paths.py
└── demo_library/
```
