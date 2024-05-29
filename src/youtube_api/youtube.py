from dotenv import load_dotenv
import os
from ytmusicapi import YTMusic
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
from constants import playlistsForMusic
import pylast
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests


class YoutubeAPI:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('YOUTUBE_API_KEY')
        lastfm_api_key = os.getenv('LASTFM_API_KEY')
        lastfm_api_secret = os.getenv('LASTFM_API_SECRET')
        spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        spotify_redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
        spotify_scope = 'user-library-read'

        self.ytmusic = YTMusic()
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.lastfm_network = pylast.LastFMNetwork(
            api_key=lastfm_api_key, api_secret=lastfm_api_secret)
        self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=spotify_client_id, client_secret=spotify_client_secret, redirect_uri=spotify_redirect_uri, scope=spotify_scope))

    def get_genre(self, artist, title, retries=20):
        try:
            results = self.spotify.search(q='artist:' + artist, type='artist')
            if results['artists']['items']:
                genres = results['artists']['items'][0]['genres']
                if genres:
                    return genres[0]
            try:
                track = self.lastfm_network.get_track(artist, title)
                top_tags = track.get_top_tags()
                if top_tags:
                    return top_tags[0].item.get_name()
            except pylast.WSError:
                pass
        except requests.exceptions.ReadTimeout:
            if retries > 0:
                print("The request to the Spotify API timed out. Retrying...")
                time.sleep(7)
                return self.get_genre(artist, title, retries-1)
        return 'Unknown'

    def get_playlist_info(self, playlist_id, retries=20):
        print(f'👉 get metadata for: {playlist_id}')
        items = []
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, 5000)
            playlist_name = playlist["title"]
            print(f'☝️ get metadata for: {playlist_name}')
        except KeyError as e:
            if retries > 0:
                print(f'🥹 Error: {e}. Retry...')
                time.sleep(5)
                return self.get_playlist_info(playlist_id, retries-1)
            else:
                print(f'🥺 Error: {e}. No more retry.')
                return {"playlist_name": playlist_name, "items": items}
        for content in playlist['tracks']:
            print(f'👉 get metadata for content: {content["title"]}')
            video_id = content['videoId']
            if video_id is None:
                video_id = self.search(playlist_id, content['title'])
            thumbnail_url = content['thumbnails'][1]['url'] if len(
                content['thumbnails']) > 1 else content['thumbnails'][0]['url']
            artists = [artist['name'] for artist in content['artists']]
            artist = ', '.join(artists[:-1]) + ' & ' + \
                artists[-1] if len(artists) > 1 else artists[0]
            item = {
                'video_id': video_id,
                'video_url': f"https://www.youtube.com/watch?v={video_id}",
                'title': content['title'],
                'thumbnail_url': thumbnail_url,
                'artist': artist,
            }
            if (content['videoType'] == 'MUSIC_VIDEO_TYPE_ATV' or content['videoType'] is None) and playlist_id in playlistsForMusic:
                item['genre'] = self.get_genre(artist, content['title'])
                if content['album'] is not None:
                    item['album'] = content['album']['name']
                else:
                    item['album'] = ''
            # OMV: Original Music Video - uploaded by original artist with actual video content
            # UGC: User Generated Content - uploaded by regular YouTube user
            # ATV: High quality song uploaded by original artist with cover image
            # OFFICIAL_SOURCE_MUSIC: Official video content, but not for a single track
            item['video_type'] = content['videoType']
            items.append(item)
        items = sorted(items, key=lambda x: (
            x['artist'], x.get('album', ''), x['title']))
        return {"playlist_name": playlist_name, "items": items}

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
