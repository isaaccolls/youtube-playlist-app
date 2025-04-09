from pytube import YouTube


def download_video(playlist_name, video_id, video_url):
    print(f"download_video {video_id}")
    if video_id is None:
        return
    video_download_path = "./downloads/mp4/" + playlist_name
    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_highest_resolution()
        stream.download(video_download_path)
    except Exception as e:
        print(f"🚫🚫 error downloading {video_id}: {str(e)}")


def download_videos(videos):
    for video in videos:
        video_id = video.split('=')[-1]
        download_video('playlist', video_id, video)


def main():
    videos = [
        'https://www.youtube.com/watch?v=p02EW3isVIo',
        'https://www.youtube.com/watch?v=UdKUtrYOV-Q'
    ]
    print('🚀 here we go!')
    download_videos(videos)
    print('✅ done!')


if __name__ == "__main__":
    main()
