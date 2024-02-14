from dotenv import load_dotenv
import os
from youtube_api.youtube import YoutubeAPI
from json_creator.json_creator import JsonCreator
from downloader.downloader import Downloader


def main():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    playlist_id = 'PL_8z4vyyerkNdojRqG-N2Z2m_Y7MiRuur'
    #
    youtube_api = YoutubeAPI(api_key)
    playlist_info = youtube_api.get_playlist_items(playlist_id)

    # Crear una instancia de JsonCreator
    json_creator = JsonCreator(playlist_info)

    # Crear el archivo JSON con la información de la playlist
    filename = "./data/playlists.json"
    json_creator.create_json(filename)

    # Crear una instancia de Downloader
    download_path = "./downloads"
    downloader = Downloader(download_path)

    # Descargar los archivos en formato mp3 o mp4
    for item in playlist_info:
        if item['type'] == 'song':
            downloader.download_audio(
                item['video_id'], item['title'], item['description'])
        elif item['type'] == 'video':
            downloader.download_video(item['video_id'])


if __name__ == "__main__":
    main()
