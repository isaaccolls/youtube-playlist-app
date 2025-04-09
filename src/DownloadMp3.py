# check playlist metadata
from ytmusicapi import YTMusic
# download mp3 from youtube
from pytubefix import YouTube, Playlist
from pytubefix.cli import on_progress
# internal project imports
from constants import playlistIdForMusic, playlistUrlForMusic, pathForMusic


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
        # loop through all items in the playlist
        for content in playlist['tracks']:
            title = content['title']
            print(f"👉 title: {title}")
            artists = content['artists']
            print(
                f"👉 artists: {', '.join([artist['name'] for artist in artists])}")

            video_id = content['videoId']
            print(f"👉 video id: {video_id}")

            # if video_id is None:
            #     print(f"❌ no video id for {content['title']}")
            #     continue
            # video_url = f"https://www.youtube.com/watch?v={video_id}"
            # print(f"👉 start download {video_url}")
            # self.download_audio(video_url)
