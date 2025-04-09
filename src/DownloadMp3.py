from pytubefix import YouTube
from pytubefix.cli import on_progress


class DownloadMp3:

    def download_audio(self, url):
        yt = YouTube(url, on_progress_callback=on_progress)
        print(f"👉 start download {yt.title}")
        ys = yt.streams.get_highest_resolution()
        ys.download()
        print(f"✅ download completed {yt.title}")

    def run(self):
        print('going for mp3 🔥🚀')
        self.download_audio("https://www.youtube.com/watch?v=kXYiU_JCYtU")
