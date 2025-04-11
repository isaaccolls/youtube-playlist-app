# check playlist metadata
from ytmusicapi import YTMusic
# download mp3 from youtube
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
# file operations
import os
import json
# internal project imports
from constants import playlistIdForMusic, playlistUrlForMusic, pathForMusic


class DownloadMp3:
    def __init__(self):
        self.playlist_url = playlistUrlForMusic
        self.playlist_id = str(playlistIdForMusic)
        self.path = pathForMusic + 'playlist.json'

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
            'album': content['album']['name'] if content['album'] is not None else '',
            'video_type': content['videoType']
        }
        return item

    def is_item_in_playlist_json(self, item, playlist_json):
        def normalize(value):
            return value.strip().lower() if isinstance(value, str) else ''
        return any(
            normalize(existing_item['title']) == normalize(item['title']) and
            normalize(existing_item['thumbnail_url']) == normalize(item['thumbnail_url']) and
            normalize(existing_item['artist']) == normalize(item['artist']) and
            normalize(existing_item['album']) == normalize(item['album'])
            for existing_item in playlist_json
        )

    def download_audio(self, url):
        yt = YouTube(url, on_progress_callback=on_progress)
        print(f"👉 start download {yt.title}")
        ys = yt.streams.get_audio_only()
        ys.download(self.path)
        print(f"✅ download completed {yt.title}")

    def run(self):
        print('going for mp3 🔥🚀')
        # get playlist info
        try:
            playlist = self.check_playlist(self.playlist_id)
            # playlist = {'tracks': []}
        except Exception as e:
            print(f"🚫 error getting playlist info: {e}")
            return
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
        # print(json.dumps(items, indent=4))
        print(f"👉 found {len(items)} items")
        # check local json file
        if os.path.exists(self.path):
            with open(self.path, 'r') as f:
                playlist_json = json.load(f)
                print(f"👉 found {len(playlist_json)} items in local json")
                matched_items = 0
                for item in items:
                    if not self.is_item_in_playlist_json(item, playlist_json):
                        print(f"👉 new song found: {item['title']}")
                        playlist_json.append({
                            'title': item['title'],
                            'thumbnail_url': item['thumbnail_url'],
                            'artist': item['artist'],
                            'album': item['album'],
                        })
                    else:
                        # print(f"✅ song already exists: {item['title']}")
                        matched_items += 1
                print(f"👉 {matched_items} songs already exist in local json")
                with open(self.path, 'w') as f:
                    json.dump(playlist_json, f, indent=2)
        # download all items
        # print(f"👉 start download {len(items)} items")
        # for item in items:
        #     video_id = item['video_id']
        #     video_url = item['video_url']
        #     title = item['title']
        #     thumbnail_url = item['thumbnail_url']
        #     artist = item['artist']
        #     album = item['album']
        #     print(f"👉 start download {title} - {artist}")
        #     self.download_audio(video_url)
