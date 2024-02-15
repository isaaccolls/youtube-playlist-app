from dotenv import load_dotenv
from youtube_api.youtube import YoutubeAPI
from json_creator.json_creator import JsonCreator
from downloader.downloader import Downloader


class Playlist:
    def __init__(self, api_key, playlist_id):
        self.api_key = api_key
        self.playlist_id = playlist_id
        self.youtube_api = YoutubeAPI(self.api_key)
        self.playlist_info = self.youtube_api.get_playlist_items(
            self.playlist_id)
        self.json_creator = JsonCreator(self.playlist_info)
        self.filename = "./data/" + self.playlist_id + "_playlist.json"
        self.download_path = "./downloads"
        self.downloader = Downloader(self.download_path)

    def process(self):
        self.json_creator.create_json(self.filename)
        for item in self.playlist_info:
            if item['type'] == 'song':
                self.downloader.download_audio(
                    item['video_id'], item['title'], item['description'])
            elif item['type'] == 'video':
                self.downloader.download_video(item['video_id'])
