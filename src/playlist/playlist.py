import os
import shutil
from youtube_api.youtube import YoutubeAPI
from json_creator.json_creator import JsonCreator
from downloader.downloader import Downloader


class Playlist:
    def __init__(self, playlist_id):
        self.playlist_id = playlist_id

    def create_directory(self, directory_name):
        if not os.path.exists(directory_name):
            os.makedirs(directory_name)
        else:
            shutil.rmtree(directory_name)
            os.makedirs(directory_name)

    def get_playlist_info(self):
        youtube_api = YoutubeAPI()
        return youtube_api.get_playlist_info(self.playlist_id)

    def create_json(self, playlist_info):
        json_creator = JsonCreator(playlist_info)
        filename = "./data/" + self.playlist_id + "_playlist.json"
        json_creator.create_json(filename)

    def get_downloader(self):
        download_path = "./downloads"
        return Downloader(download_path)

    def process_music(self):
        print(f'go for music 🎵 {self.playlist_id}')
        playlist_data = self.get_playlist_info()
        playlist_info = playlist_data['items']
        playlist_name = playlist_data['playlist_name']
        self.create_directory(f"./downloads/mp3/{playlist_name}")
        self.create_json(playlist_info)
        downloader = self.get_downloader()
        for item in playlist_info:
            if item['video_type'] != 'MUSIC_VIDEO_TYPE_ATV':
                print(f"🚫 not music {item['title']} // {item['artist']}")
            # else:
            #     downloader.download_audio(
            #         playlist_name, item['video_id'], item['video_url'], item['title'], item['thumbnail_url'], item['artist'], item['album'])

    def process_video(self):
        print(f'go for video 📺 {self.playlist_id}')
        playlist_data = self.get_playlist_info()
        playlist_info = playlist_data['items']
        playlist_name = playlist_data['playlist_name']
        self.create_directory(f"./downloads/mp4/{playlist_name}")
        self.create_json(playlist_info)
        downloader = self.get_downloader()
        for item in playlist_info:
            if item['video_type'] == 'MUSIC_VIDEO_TYPE_ATV':
                print(f"🚫 not a video {item['video_id']}")
            # else:
            #     downloader.download_video(
            #         playlist_name, item['video_id'], item['video_url'])
