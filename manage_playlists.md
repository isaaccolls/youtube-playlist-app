# manage_playlists.py

Script interactivo para administrar playlists M3U. Mantiene `all.m3u` sincronizada con todos los archivos MP3 del directorio y permite clasificar canciones en playlists de género de forma interactiva.

## Requisitos

- Python 3.10+
- `mpv` — reproducción de audio
- `ffprobe` (parte de FFmpeg) — lectura de duración de archivos MP3 y verificación de que son legibles

## Uso

```bash
python3 manage_playlists.py
```

El script requiere un terminal interactivo (no funciona redirigido o en background).

## Estructura esperada

```
data/mp3/
├── all.m3u
├── bachata.m3u
├── bailoteo.m3u
├── bolero.m3u
├── bossanova.m3u
├── classical.m3u
├── cumbia.m3u
├── electro.m3u
├── gaita.m3u
├── jazz.m3u
├── llanera.m3u
├── lofi.m3u
├── lollipop.m3u
├── mariachi.m3u
├── merengue.m3u
├── rap.m3u
├── reggae.m3u
├── rock.m3u
├── salsa.m3u
├── tambor.m3u
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

## Al iniciar — Canciones por playlist

Lo primero que muestra el script es la cantidad de canciones que contiene cada playlist (`all` y luego los géneros en orden alfabético), tal como están en disco antes de cualquier cambio:

```
Canciones por playlist:
  all        5843    bachata       9    bailoteo    486
  bolero        9    bossanova     3    classical    85
  ...
```

Si existe algún otro `.m3u` en el directorio, también se lista.

## Fase 1 — Sincronización de `all.m3u`

Luego, el script compara los archivos `.mp3` presentes en disco con las entradas de `all.m3u`:

- **Entradas faltantes**: canciones en disco que no están en `all.m3u`. Se agregan automáticamente. La duración se obtiene con `ffprobe` usando 8 hilos en paralelo; se muestra una barra de progreso.
- **Entradas obsoletas**: entradas en `all.m3u` cuyo archivo ya no existe en disco. Se eliminan.
- **Sin cambios**: si todo está al día, se informa y se continúa.

Los metadatos existentes (`#EXTINF`) se preservan; solo se modifican las entradas afectadas.

## Fase 1b — Verificación de integridad

Después de sincronizar, se valida cada playlist `.m3u` del directorio (incluida `all.m3u`) línea a línea contra el formato descrito arriba. La verificación es de sólo lectura: no corrige ni modifica ningún archivo.

Antes de validar, se lee con `ffprobe` la duración real de todos los mp3 del directorio (8 hilos en paralelo, con barra de progreso; alrededor de un minuto para ~6000 archivos). Con ese dato se comprueba que cada mp3 referenciado sea legible y que la duración de su `#EXTINF` siga siendo la del archivo.

Por cada playlist con problemas se listan el número de línea y el detalle (hasta 20 por playlist, los errores primero), seguido de un total general.

**Errores** (la playlist está dañada):

- no se puede leer el archivo, o está vacío
- falta la cabecera `#EXTM3U`
- línea con codificación UTF-8 inválida
- `#EXTINF` malformado: sin coma, duración no numérica o título vacío
- `#EXTINF` sin archivo a continuación
- entrada sin `#EXTINF` previo
- entrada duplicada
- entrada con ruta (se espera sólo el nombre del archivo)
- el archivo no existe en disco (mp3 renombrado o eliminado)
- el mp3 existe pero está vacío (0 bytes)
- `ffprobe` no puede leer el mp3 (archivo corrupto)

**Avisos** (la playlist funciona, pero no está en el formato que escribe el script):

- BOM UTF-8, saltos de línea CRLF o falta el salto de línea final
- líneas en blanco, o con espacios al inicio o al final
- comentarios o directivas no reconocidas (se perderían al guardar)
- duración `0` o negativa en `#EXTINF`
- la duración del `#EXTINF` no coincide con la que reporta `ffprobe` (mp3 reemplazado o truncado después de agregarlo)
- el título del `#EXTINF` no corresponde al nombre del archivo
- la playlist de un género no existe en disco
- `.m3u` sin tecla asignada (el script no lo administra)

Si hay al menos un error, el script se detiene antes de la fase 2 y pide confirmación: `Enter` / `Espacio` continúa de todos modos, `q` sale con código `1`. Los avisos no detienen la ejecución.

Además se reportan los archivos mp3 cuyo nombre contiene `#`, `%` o `?`, que rompen el import de playlists en reproductores que resuelven las rutas como URI (p. ej. VLC iOS).

## Fase 2 — Clasificación interactiva

Una canción se considera **sin categorizar** si no aparece en ninguna de las 20 playlists de género. El script procesa todas las canciones sin categorizar en orden alfabético.

Por cada canción:

1. Se muestra el contador de progreso y el nombre de la canción.
2. Se inicia la reproducción con `mpv` en segundo plano.
3. El script espera entrada del teclado.

### Controles

| Tecla               | Acción                        |
| ------------------- | ----------------------------- |
| `a`                 | toggle classical              |
| `b`                 | toggle bailoteo               |
| `o`                 | toggle bossanova              |
| `h`                 | toggle bachata                |
| `c`                 | toggle cumbia                 |
| `d`                 | toggle bolero                 |
| `e`                 | toggle electro                |
| `g`                 | toggle reggae                 |
| `i`                 | toggle gaita                  |
| `j`                 | toggle jazz                   |
| `f`                 | toggle lofi                   |
| `k`                 | toggle rock                   |
| `l`                 | toggle llanera                |
| `m`                 | toggle merengue               |
| `p`                 | toggle lollipop               |
| `r`                 | toggle rap                    |
| `s`                 | toggle salsa                  |
| `t`                 | toggle tambor                 |
| `v`                 | toggle vallenato              |
| `x`                 | toggle mariachi               |
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
