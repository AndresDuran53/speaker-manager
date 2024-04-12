import spotipy
from spotipy.oauth2 import SpotifyOAuth
from utils.custom_logging import CustomLogging
import time

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

class SpotifyService:
    home_spotify_name = "Spotifyd@sneer-server"

    def __init__(self, config_data, logger=CustomLogging("logs/spotify.log")):
        self.logger = logger
        self.logger.info("Creating Spotify Service...")
        self.config = SpotifyConfig.from_json(config_data)
        self.wasPaused = False
        self.last_volume = 0
        self.volume_decrease = 0.8

    def get_spotify_object(self):
        sp = None
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.config.client_id,
                                                        client_secret=self.config.client_secret,
                                                        redirect_uri=self.config.redirect_url,
                                                        scope=self.config.scope))
        except:
            print("[Error] Not able to authorize profile")   
        return sp

    def pause_song_if_necessary(self):
        try:
            sp = self.get_spotify_object()
            is_raspotify_device_playing = self.is_raspotify_playing(sp)
            self.logger.info(f"is_raspotify_device_playing: {is_raspotify_device_playing}")
            if(is_raspotify_device_playing):
                raspotify_device = self.get_raspotify_device(sp)
                actual_volume = raspotify_device.volume_percent
                self.last_volume = actual_volume
                self.logger.info(f"actual_volume: {actual_volume}")
                new_volume = int(actual_volume*self.volume_decrease)
                self.logger.info(f"New Volume : {new_volume}")
                sp.volume(new_volume)
                #sp.pause_playback(raspotify_id)
                self.wasPaused = True
                time.sleep(0.5)
        except:
            print("[Error] Not able to pause song")   

    def play_song(self):
        try:
            sp = self.get_spotify_object()
            if(self.wasPaused):
                #sp.start_playback()
                raspotify_device = self.get_raspotify_device(sp)
                self.logger.info(f"Setting volumen again to: {self.last_volume}")
                sp.volume(self.last_volume)
                self.wasPaused = False
        except:
            print("[Error] Not able to authorize profile")   

    def is_playing(self,sp=None):
        try:
            if(sp is None): sp = self.get_spotify_object()
            playing_track = sp.current_user_playing_track()
            if(playing_track!=None):
                isPlaying = playing_track[u'is_playing']
                return isPlaying
        except:
            print("[Error] Not able to get song status")    
        return False

    def get_devices(self,sp=None) -> list[SpotifyDevice]:
        if(sp is None): sp = self.get_spotify_object()
        devices_list = sp.devices()
        spotifyDevice_list = SpotifyDevice.from_json_list(devices_list)
        return spotifyDevice_list
    
    def get_raspotify_device(self,sp=None):
        if(sp is None): sp = self.get_spotify_object()
        spotifyDevice_list = self.get_devices(sp)
        for spotifyDevice in spotifyDevice_list:
            if(spotifyDevice.name == self.home_spotify_name):
                return spotifyDevice
        return None
    
    def get_raspotify_id(self,sp=None):
        if(sp is None): sp = self.get_spotify_object()
        spotifyDevice_list = self.get_devices(sp)
        for spotifyDevice in spotifyDevice_list:
            if(spotifyDevice.name == self.home_spotify_name):
                return spotifyDevice.id
        return None
    
    def is_raspotify_playing(self,sp=None):
        if(sp is None): sp = self.get_spotify_object()
        raspotify_device = self.get_raspotify_device(sp)
        if(raspotify_device is not None and raspotify_device.is_active):
            playing_track = sp.current_user_playing_track()
            if(playing_track is not None):
                isPlaying = playing_track[u'is_playing']
                return isPlaying    
        return False        

    def test(self):
        self.pause_song_if_necessary()