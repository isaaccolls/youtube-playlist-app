from youtube_api.youtube import YoutubeAPI
from json_creator.json_creator import JsonCreator
from downloader.downloader import Downloader


class Playlist:
    def __init__(self, playlist_id):
        self.playlist_id = playlist_id

    def processMusic(self):
        print(f'go for music 🎵 {self.playlist_id}')
        youtube_api = YoutubeAPI()
        playlist_info = youtube_api.get_playlist_info(self.playlist_id)
        json_creator = JsonCreator(playlist_info)
        filename = "./data/" + self.playlist_id + "_playlist.json"
        json_creator.create_json(filename)
        download_path = "./downloads"
        downloader = Downloader(download_path)
        for item in playlist_info:
            if item['vide_type'] == 'MUSIC_VIDEO_TYPE_ATV':
                downloader.download_audio(
                    item['video_id'], item['video_url'], item['title'], item['thumbnail_url'], item['artist'], item['album'])
            else:
                print(f"🚫 not music {item['title']} // {item['artist']}")

    def processVideo(self):
        print(f'go for video 🎥 {self.playlist_id}')
        youtube_api = YoutubeAPI()
        playlist_info = youtube_api.get_playlist_info(self.playlist_id)
        json_creator = JsonCreator(playlist_info)
        filename = "./data/" + self.playlist_id + "_playlist.json"
        json_creator.create_json(filename)
        download_path = "./downloads"
        downloader = Downloader(download_path)
        for item in playlist_info:
            if item['vide_type'] == 'MUSIC_VIDEO_TYPE_ATV':
                print(f'🚫 not a video {item['title']} // {item['artist']}')
            else:
                downloader.download_video(item['video_id'], item['video_url'])
