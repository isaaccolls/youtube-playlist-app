# check playlist metadata
from ytmusicapi import YTMusic
# download mp3 from youtube
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
# internal project imports
from constants import playlistIdForMusic, playlistUrlForMusic, pathForMusic
# import json


class DownloadMp3:
    def __init__(self):
        self.playlist_url = playlistUrlForMusic
        self.playlist_id = str(playlistIdForMusic)
        self.path = pathForMusic

    def check_playlist(self, playlist_id):
        print(f"👉 Checking playlist {playlist_id}")
        playlist_id = str(playlist_id)
        ytmusic = YTMusic()
        return ytmusic.get_playlist(playlist_id, 4000, False, 0)

    def get_thumbnail_url(self, content):
        return content['thumbnails'][1]['url'] if len(content['thumbnails']) > 1 else content['thumbnails'][0]['url']

    def get_artist_string(self, artists):
        if len(artists) > 1:
            return ', '.join(artist['name'] for artist in artists[:-1]) + ' & ' + artists[-1]['name']
        return artists[0]['name']

    def create_item_to_download(self, content):
        # print(f'👉 get metadata for content: {content["title"]}')
        video_id = content['videoId']
        thumbnail_url = self.get_thumbnail_url(content)
        artist = self.get_artist_string(content['artists'])
        item = {
            'video_id': video_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'title': content['title'],
            'thumbnail_url': thumbnail_url,
            'artist': artist,
            'video_type': content['videoType']
        }
        return item

    def download_audio(self, url):
        yt = YouTube(url, on_progress_callback=on_progress)
        print(f"👉 start download {yt.title}")
        ys = yt.streams.get_audio_only()
        ys.download(self.path)
        print(f"✅ download completed {yt.title}")

    def run(self):
        print('going for mp3 🔥🚀')
        # get playlist info
        playlist = self.check_playlist(self.playlist_id)
        # print(json.dumps(playlist, indent=4))
        # loop through all items in the playlist
        items = []
        for content in playlist['tracks']:
            # check video type
            video_type = content['videoType']
            if video_type != 'MUSIC_VIDEO_TYPE_ATV':
                print(f"❌ not music video type atv {content['title']}")
                continue
            # check video id
            video_id = content['videoId']
            if video_id is None:
                print(f"❌ no videoId: {content['title']} {content['artists']}")
                continue
            items.append(self.create_item_to_download(content))
        print(f"👉 found {len(items)} items")
        # video_url = f"https://www.youtube.com/watch?v={video_id}"
        # print(f"👉 start download {video_url}")
        # self.download_audio(video_url)
