import os
import eyed3
from pytube import YouTube
from urllib.error import HTTPError
from moviepy.editor import AudioFileClip


class Downloader:
    def __init__(self, download_path):
        self.download_path = download_path

    def download_video(self, video_id):
        url = f"https://www.youtube.com/watch?v={video_id}"
        video_download_path = self.download_path + "/mp4"
        try:
            print(f"Downloading video: {video_id}")
            yt = YouTube(url)
            stream = yt.streams.get_highest_resolution()
            stream.download(video_download_path)
        except HTTPError:
            print(f"Video {video_id} is not available.")

    def download_audio(self, video_id, title, description):
        url = f"https://www.youtube.com/watch?v={video_id}"
        audio_download_path = self.download_path + "/mp3"
        try:
            print(f"Downloading audio: {title}")
            yt = YouTube(url)
            stream = yt.streams.get_audio_only()
            filename = stream.default_filename
            mp4_filename = os.path.join(audio_download_path, filename)
            mp3_filename = os.path.join(
                audio_download_path, filename.rsplit(".", 1)[0] + ".mp3")
            stream.download(audio_download_path, filename=filename)
            # Convert mp4 to mp3
            audioclip = AudioFileClip(mp4_filename)
            audioclip.write_audiofile(mp3_filename)
            # Add ID3 tags
            audiofile = eyed3.load(mp3_filename)
            audiofile.tag.artist = yt.author
            audiofile.tag.album = yt.title
            audiofile.tag.title = title
            audiofile.tag.comments.set(description)
            audiofile.tag.save()
            # Remove the mp4 file
            os.remove(mp4_filename)
        except HTTPError:
            print(f"Video {video_id} is not available.")
