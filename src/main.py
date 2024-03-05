from playlist.playlist import Playlist
from constants import playlistsForMusic, playlistsForVideo


def main():
    print('🚀 here we go!')
    for playlist_id in playlistsForMusic:
        Playlist(playlist_id).processMusic()
    for playlist_id in playlistsForVideo:
        Playlist(playlist_id).processVideo()
    print('✅ done!')


if __name__ == "__main__":
    main()
