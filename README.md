# Youtube Playlist App

Este proyecto es una aplicación de Python que permite acceder a una playlist pública de YouTube, crear un archivo JSON con la información de la playlist y descargar los archivos de la playlist en formato mp3 o mp4.

## Estructura del Proyecto

El proyecto tiene la siguiente estructura de directorios:

```
youtube-playlist-app
├── src
│   ├── main.py
│   ├── youtube_api
│   │   └── youtube.py
│   ├── json_creator
│   │   └── json_creator.py
│   ├── downloader
│   │   └── downloader.py
│   └── utils
│       └── utils.py
├── data
│   └── playlists.json
├── downloads
│   ├── mp3
│   └── mp4
├── requirements.txt
└── README.md
```

## Requisitos

Para ejecutar este proyecto, necesitarás Python 3 y las dependencias listadas en `requirements.txt`.

## Uso

Para usar esta aplicación, sigue estos pasos:

1. Clona este repositorio en tu máquina local.
2. Instala las dependencias con `pip install -r requirements.txt`.
3. Ejecuta `python src/main.py` para iniciar la aplicación.

## Funcionalidad

La aplicación realiza las siguientes tareas:

- Accede a una playlist pública de YouTube.
- Crea un archivo JSON con la información de la playlist, incluyendo si cada elemento es un video o una canción, y metadatos relevantes como el artista de la canción, el nombre, el álbum, la portada, etc.
- Descarga los archivos de la playlist en formato mp3 o mp4, dependiendo de si son canciones o videos, respectivamente. Los archivos se descargan con la máxima calidad de audio y la mejor resolución disponible.

## Contribuciones

Las contribuciones a este proyecto son bienvenidas. Por favor, abre un issue o un pull request para sugerir cambios o mejoras.

# Actualizar yt-dlp (YouTube requiere EJS + runtime JS)

```bash
pip3 install -U "yt-dlp[default]"
```

Desde 2026, YouTube exige **EJS** (scripts JS) y un **runtime de JavaScript**. Sin esto verás "Signature solving failed" / "n challenge solving failed" y solo se ofrecerán imágenes.

1. **Instalar yt-dlp con extras** (ya incluye `yt-dlp-ejs`):

   ```bash
   pip3 install -U "yt-dlp[default]"
   ```

2. **Instalar un runtime de JavaScript** (solo uno):
   - **Deno** (recomendado): https://docs.deno.com/runtime/getting_started/installation/  
     Linux: `curl -fsSL https://deno.land/install.sh | sh`
   - **Node.js** (v20+): https://nodejs.org/  
     Luego en `~/.config/yt-dlp/config` o en las opciones del script añadir: `--js-runtimes node`

# Detectar mp3 corruptos

`src/checkCorruptedFiles.py` revisa todos los mp3 de `data/mp3/` y detecta archivos
**realmente corruptos**: truncados (descarga/conversión incompleta) o ilegibles. No
detecta artefactos de calidad de audio (por ejemplo, el "crepitar" que puede oírse en
canciones con transitorios fuertes de viento/percusión), ya que eso no es corrupción
del archivo sino una característica de la codificación original.

Por defecto solo lista los archivos corruptos encontrados, sin borrar nada:

```bash
python3 src/checkCorruptedFiles.py
```

Para borrar los mp3 corruptos y su entrada correspondiente en `playlist.json`, añade `--delete`:

```bash
python3 src/checkCorruptedFiles.py --delete
```

Opcionalmente se puede ajustar la cantidad de archivos analizados en paralelo (por defecto 8):

```bash
python3 src/checkCorruptedFiles.py --workers 12
```

# Importar mp3 descargados manualmente

`src/importManualMp3.py` normaliza tags ID3 y nombre de archivo (mismas reglas
que `DownloadMp3`/`checkFiles`) de los mp3 en `data/mp3-manual/`, y los mueve
a `data/mp3/` agregándolos a `playlist.json`. Por cada archivo pide confirmar/
corregir title, artist y album (`Enter` mantiene el valor actual, `-` lo deja
vacío, `skip` omite el archivo).

```bash
python3 src/importManualMp3.py
```

Para ver qué haría sin mover archivos ni escribir nada, añade `--dry-run`:

```bash
python3 src/importManualMp3.py --dry-run
```

# cookies

1. Open a new private browsing/incognito window and log into YouTube
1. In same window and same tab from step 1, navigate to https://www.youtube.com/robots.txt (this should be the only private/incognito browsing tab open)
1. Export youtube.com cookies from the browser, then close the private browsing/incognito window so that the session is never opened in the browser again.

# display tecnical information

run: `ffprobe A\ Day\ To\ Remember\ -\ For\ Those\ Who\ Have\ Heart\ -\ Monument.mp3`
