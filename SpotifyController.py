import spotipy
import json
from spotipy.oauth2 import SpotifyOAuth


class SpotifyController:

    def __init__(self, config):
        self.config = config
        self.wasPaused = False

    def pause_song(self):
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.config.client_id,
                                                       client_secret=self.config.client_secret,
                                                       redirect_uri=self.config.redirect_url,
                                                       scope=self.config.scope))
        raspotifyId = self.get_raspotify_id()
        playing_track = sp.current_user_playing_track()
        if(playing_track!=None):
            isPlaying = sp.current_user_playing_track()[u'is_playing']
            if(isPlaying and raspotifyId != None):
                sp.pause_playback(raspotifyId)
                self.wasPaused = True

    def play_song(self):
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.config.client_id,
                                                       client_secret=self.config.client_secret,
                                                       redirect_uri=self.config.redirect_url,
                                                       scope=self.config.scope))
        if(self.wasPaused):
            sp.start_playback()
            self.wasPaused = False

    def get_devices(self):
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.config.client_id,
                                                       client_secret=self.config.client_secret,
                                                       redirect_uri=self.config.redirect_url,
                                                       scope=self.config.scope))
        devices_list = sp.devices()
        spotifyDevice_list = SpotifyDevice.from_json_list(devices_list)
        return spotifyDevice_list
    
    def get_raspotify_id(self):
        spotifyDevice_list = self.get_devices()
        for spotifyDevice in spotifyDevice_list:
            if(spotifyDevice.name == 'raspotify (homeassistant)'):
                return spotifyDevice.id
        return None
            

class SpotifyDevice:
    def __init__(self, device_dict):
        self.id = device_dict.get("id", None)
        self.is_active = device_dict.get("is_active", False)
        self.is_private_session = device_dict.get("is_private_session", False)
        self.is_restricted = device_dict.get("is_restricted", False)
        self.name = device_dict.get("name", None)
        self.type = device_dict.get("type", None)
        self.volume_percent = device_dict.get("volume_percent", None)

    @classmethod
    def from_json(cls, device):
        device_obj = cls(device)
        return device_obj


    @classmethod
    def from_json_list(cls, json_obj):
        device_list = []
        for device in json_obj["devices"]:
            device_obj = cls.from_json(device)
            device_list.append(device_obj)
        return device_list

class SpotifyConfig:
    def __init__(self, spotify_dict):
        self.client_id = spotify_dict.get('clientId', None)
        self.client_secret = spotify_dict.get('clientSecret', None)
        self.redirect_url = spotify_dict.get('redirectUrl', None)
        self.scope = "user-read-playback-state user-modify-playback-state user-top-read user-read-recently-played"

    @classmethod
    def from_json(cls, config_data):
        return SpotifyConfig(config_data.get('spotify', {}))