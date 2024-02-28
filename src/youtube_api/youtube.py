from ytmusicapi import YTMusic
import time


class YoutubeAPI:
    def __init__(self):
        self.ytmusic = YTMusic()

    def get_playlist_info(self, playlist_id, retries=3):
        print(f'👉 get metadata for: {playlist_id}')
        items = []
        try:
            playlist = self.ytmusic.get_playlist(playlist_id)
            print(f'☝️ get metadata for: {playlist["title"]}')
        except KeyError as e:
            if retries > 0:
                print(f'🥹 Error: {e}. Retry...')
                time.sleep(2)
                return self.get_playlist_info(playlist_id, retries-1)
            else:
                print(f'🥺 Error: {e}. No more retry.')
                return items
        for content in playlist['tracks']:
            video_id = content['videoId']
            thumbnail_url = content['thumbnails'][1]['url'] if len(
                content['thumbnails']) > 1 else content['thumbnails'][0]['url']
            album = content['album']['name'] if content['album'] is not None else ''
            artists = [artist['name'] for artist in content['artists']]
            artist = ', '.join(artists[:-1]) + ' & ' + \
                artists[-1] if len(artists) > 1 else artists[0]
            items.append({
                'video_id': video_id,
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'title': content['title'],
                'thumbnail_url': thumbnail_url,
                'artist': artist,
                'album': album,
                # OMV: Original Music Video - uploaded by original artist with actual video content
                # UGC: User Generated Content - uploaded by regular YouTube user
                # ATV: High quality song uploaded by original artist with cover image
                # OFFICIAL_SOURCE_MUSIC: Official video content, but not for a single track
                'vide_type': content['videoType']
            })
        items = sorted(items, key=lambda x: (
            x['artist'], x['album'], x['title']))
        return items
