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

# cookies

1. Open a new private browsing/incognito window and log into YouTube
1. In same window and same tab from step 1, navigate to https://www.youtube.com/robots.txt (this should be the only private/incognito browsing tab open)
1. Export youtube.com cookies from the browser, then close the private browsing/incognito window so that the session is never opened in the browser again.
