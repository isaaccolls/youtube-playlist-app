from dotenv import load_dotenv
import os
from ytmusicapi import YTMusic
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time


class YoutubeAPI:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
        self.ytmusic = YTMusic()
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_playlist_info(self, playlist_id, retries=3):
        print(f'👉 get metadata for: {playlist_id}')
        items = []
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, 5000)
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
            if video_id is None:
                video_id = self.search(playlist_id, content['title'])
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

    def search(self, playlist_id, title):
        try:
            page_token = None
            while True:
                request = self.youtube.playlistItems().list(
                    part="snippet",
                    maxResults=50,
                    playlistId=playlist_id,
                    pageToken=page_token
                )
                response = request.execute()
                for item in response['items']:
                    if item['snippet']['title'].lower() == title.lower():
                        return item['snippet']['resourceId']['videoId']
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            return None
        except HttpError as e:
            print(f'An HTTP error {e.resp.status} occurred:\n{e.content}')
