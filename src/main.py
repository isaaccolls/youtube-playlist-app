from dotenv import load_dotenv
import os
from playlist.playlist import Playlist


def main():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    playlists = [
        # 🍭-lolliPop
        'PL_8z4vyyerkNdojRqG-N2Z2m_Y7MiRuur'
    ]
    for playlist in playlists:
        Playlist(api_key, playlist).process()


if __name__ == "__main__":
    main()
