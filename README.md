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
