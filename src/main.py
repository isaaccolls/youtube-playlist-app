from dotenv import load_dotenv
import os
from playlist.playlist import Playlist
from constants import playlists


def main():
    load_dotenv()
    api_key = os.getenv('YOUTUBE_API_KEY')
    for playlist in playlists:
        Playlist(api_key, playlist).process()


if __name__ == "__main__":
    main()
