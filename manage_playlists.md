# manage_playlists.py

Script interactivo para administrar playlists M3U. Mantiene `all.m3u` sincronizada con todos los archivos MP3 del directorio y permite clasificar canciones en playlists de género de forma interactiva.

## Requisitos

- Python 3.10+
- `mpv` — reproducción de audio
- `ffprobe` (parte de FFmpeg) — lectura de duración de archivos MP3

## Uso

```bash
python3 manage_playlists.py
```

El script requiere un terminal interactivo (no funciona redirigido o en background).

## Estructura esperada

```
data/mp3/
├── all.m3u
├── bailoteo.m3u
├── classical.m3u
├── cumbia.m3u
├── electro.m3u
├── jazz.m3u
├── llanera.m3u
├── lollipop.m3u
├── merengue.m3u
├── rap.m3u
├── reggae.m3u
├── rock.m3u
├── salsa.m3u
├── vallenato.m3u
└── *.mp3   (archivos de audio)
```

Los archivos `.m3u` son creados automáticamente si no existen.

## Formato M3U

Los archivos usan el formato extendido `#EXTM3U`:

```
#EXTM3U
#EXTINF:219,Taylor Swift - Shake It Off
Taylor Swift - 1989 (Deluxe) - Shake It Off.mp3
```

Los nombres de archivo en las playlists son relativos (sin ruta), ya que las playlists y los MP3 están en el mismo directorio. El título en `#EXTINF` se deriva del nombre de archivo con el formato `Artista - Título` (omitiendo el álbum).

## Fase 1 — Sincronización de `all.m3u`

Al iniciar, el script compara los archivos `.mp3` presentes en disco con las entradas de `all.m3u`:

- **Entradas faltantes**: canciones en disco que no están en `all.m3u`. Se agregan automáticamente. La duración se obtiene con `ffprobe` usando 8 hilos en paralelo; se muestra una barra de progreso.
- **Entradas obsoletas**: entradas en `all.m3u` cuyo archivo ya no existe en disco. Se eliminan.
- **Sin cambios**: si todo está al día, se informa y se continúa.

Los metadatos existentes (`#EXTINF`) se preservan; solo se modifican las entradas afectadas.

## Fase 2 — Clasificación interactiva

Una canción se considera **sin categorizar** si no aparece en ninguna de las 13 playlists de género. El script procesa todas las canciones sin categorizar en orden alfabético.

Por cada canción:

1. Se muestra el contador de progreso y el nombre de la canción.
2. Se inicia la reproducción con `mpv` en segundo plano.
3. El script espera entrada del teclado.

### Controles

| Tecla               | Acción                        |
| ------------------- | ----------------------------- |
| `a`                 | toggle classical              |
| `b`                 | toggle bailoteo               |
| `c`                 | toggle cumbia                 |
| `e`                 | toggle electro                |
| `g`                 | toggle reggae                 |
| `j`                 | toggle jazz                   |
| `k`                 | toggle rock                   |
| `l`                 | toggle llanera                |
| `m`                 | toggle merengue               |
| `p`                 | toggle lollipop               |
| `r`                 | toggle rap                    |
| `s`                 | toggle salsa                  |
| `v`                 | toggle vallenato              |
| `Enter` / `Espacio` | confirmar selección y avanzar |
| `q`                 | guardar todo y salir          |
| `Ctrl+C`            | guardar todo y salir          |

Las teclas de género funcionan como **toggle**: presionar la misma tecla dos veces quita el género de la selección. Se pueden combinar varios géneros antes de confirmar con Enter.

Si se confirma sin seleccionar ningún género, la canción queda saltada (no se agrega a ninguna playlist, y aparecerá de nuevo en la próxima ejecución del script).

### Guardado

Las playlists se escriben a disco:

- Al presionar `q`
- Al interrumpir con `Ctrl+C`
- Al terminar de clasificar todas las canciones

Esto garantiza que el progreso no se pierde aunque la sesión se interrumpa. En la siguiente ejecución, el script retoma desde las canciones aún sin categorizar.

### Deduplicación

Antes de agregar una canción a una playlist, el script verifica que no esté ya presente. No se generan duplicados aunque el script se ejecute múltiples veces.
