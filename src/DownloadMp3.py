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
# asd
import eyed3
import requests
from moviepy import *

from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3

from yt_dlp import YoutubeDL


class DownloadMp3:
    def __init__(self):
        self.playlist_url = playlistUrlForMusic
        self.playlist_id = str(playlistIdForMusic)
        self.path_playlist = pathForMusic + 'playlist.json'
        self.path_file = pathForMusic

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

    def download_audio(self, file_name, video_url, title, album, artist, thumbnail_url):
        print(f"👉 start download {title}")

        # Define the file name with .mp3 extension
        file_path = os.path.join(self.path_file, file_name)
        mp3_file_name = f"{file_name}.mp3"
        mp3_file_path = os.path.join(self.path_file, mp3_file_name)

        # Use yt-dlp to download the audio and convert to MP3
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': file_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except Exception as e:
            print(f"🚫 Error downloading {title}: {e}")
            return

        # Set metadata for .mp3 file
        try:
            audiofile = eyed3.load(mp3_file_path)
            if audiofile.tag is None:
                audiofile.initTag()
            # Set ID3 tags
            audiofile.tag.title = title
            audiofile.tag.artist = artist
            audiofile.tag.album = album

            # Download and set thumbnail as album cover
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                with open("thumbnail.jpg", "wb") as img_file:
                    img_file.write(response.content)
                with open("thumbnail.jpg", "rb") as img_file:
                    img_data = img_file.read()
                audiofile.tag.images.set(3, img_data, "image/jpeg")
                os.remove("thumbnail.jpg")

            audiofile.tag.save()
        except Exception as e:
            print(f"🚫 Error setting metadata for .mp3: {e}")
            return

        print(f"✅ download completed and saved as {mp3_file_name}")

    def run(self):
        print('going for mp3 🔥🚀')
        # get playlist info
        try:
            playlist = self.check_playlist(self.playlist_id)
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
        if os.path.exists(self.path_playlist):
            with open(self.path_playlist, 'r') as f:
                playlist_json = json.load(f)
                print(f"👉 found {len(playlist_json)} items in local json")
                matched_items = 0
                for item in items[:]:
                    if not self.is_item_in_playlist_json(item, playlist_json):
                        # print(f"👉 new song found: {item['title']}")
                        playlist_json.append({
                            'title': item['title'],
                            'thumbnail_url': item['thumbnail_url'],
                            'artist': item['artist'],
                            'album': item['album'],
                        })
                    else:
                        # print(f"✅ song already exists: {item['title']}")
                        items.remove(item)
                        matched_items += 1
                print(f"👉 {matched_items} songs already exist in local json")
                with open(self.path_playlist, 'w') as f:
                    json.dump(playlist_json, f, indent=2)
        # download all items
        print(f"👉 start download {len(items)} items 🔥")
        for item in items:
            album_part_for_file_name = f" - {item['album']}" if item['album'] else ''
            #
            file_name = f"{item['title']} - {item['artist']}{album_part_for_file_name}"
            # file_path = os.path.join(self.path_file, file_name)
            #
            mp3_file_name = f"{file_name}.mp3"
            mp3_file_path = os.path.join(self.path_file, mp3_file_name)
            if os.path.exists(mp3_file_path):
                print(f"✅ {file_name} already exists locally, skipping download.")
                continue
            print(f"👉 {file_name} not found locally, downloading...")
            self.download_audio(file_name, item['video_url'], item['title'],
                                item['album'], item['artist'], item['thumbnail_url'])
