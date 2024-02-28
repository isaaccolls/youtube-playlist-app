from playlist.playlist import Playlist
from constants import playlists


def main():
    print(f'🚀 here we go!')
    for playlist_id in playlists:
        Playlist(playlist_id).process()
    print(f'✅ done!')


if __name__ == "__main__":
    main()
