import spotipy
from spotipy.oauth2 import SpotifyOAuth
from utils.custom_logging import CustomLogging
from datetime import datetime
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
        self.home_spotify_name = "Spotify-HomeServer"
        self.scope = "user-read-playback-state user-modify-playback-state user-top-read user-read-recently-played"

    @classmethod
    def from_json(cls, config_data):
        return SpotifyConfig(config_data.get('spotify', {}))

class SpotifyService:
    _is_spotify_playing: bool = False
    _playing_last_modified: datetime = None
    _librespot_device = None
    _device_last_modified: datetime = None

    def __init__(self, config_data, logger=CustomLogging("logs/spotify.log")):
        self.logger = logger
        self.logger.info("Creating Spotify Service...")
        self.config = SpotifyConfig.from_json(config_data)
        self.home_spotify_name = self.config.home_spotify_name
        self.wasPaused = False
        self.last_volume = 0
        self.volume_decrease = 0.8
        self.sp = self.get_spotify_object()

    def get_spotify_object(self) -> spotipy.Spotify:
        sp = None
        try:
            sp = spotipy.Spotify(retries=0, auth_manager=SpotifyOAuth(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                redirect_uri=self.config.redirect_url,
                scope=self.config.scope))
        except:
            print("[Error] Not able to authorize profile")
        return sp
    
    def update_is_playing(self, sp: spotipy.Spotify) -> bool:
        if(not self.can_update(self._playing_last_modified,30)): return self._is_spotify_playing

        isPlaying = False
        try:
            playing_track = sp.current_user_playing_track()
            if(playing_track is not None):
                isPlaying = playing_track[u'is_playing']
        except:
            print("[Error] Not able to get song status")
        self._playing_last_modified = datetime.now()
        self._is_spotify_playing = isPlaying  
        return isPlaying
    
    def get_devices(self, sp: spotipy.Spotify) -> list[SpotifyDevice]:
        spotifyDevice_list = []
        try:
            devices_list = sp.devices()
            spotifyDevice_list = SpotifyDevice.from_json_list(devices_list)
        except:
            print("[Error] Not able to get devices")
        return spotifyDevice_list
    
    def update_librespot_device(self, sp: spotipy.Spotify):
        if(not self.can_update(self._device_last_modified,10)): return self._librespot_device

        spotifyDevice_list = self.get_devices(sp)
        for spotifyDevice in spotifyDevice_list:
            if(spotifyDevice.name == self.home_spotify_name):
                self._device_last_modified = datetime.now()
                self._librespot_device = spotifyDevice
                return spotifyDevice
        self._device_last_modified = datetime.now()
        self._librespot_device = None
        return None

    def can_update(self, last_time: datetime, seconds_to_wait: int) -> True:
        if(last_time is None): return True
        current_time = datetime.now()
        time_difference = current_time - last_time
        if time_difference.total_seconds() >= seconds_to_wait:
            return True
        else:
            return False
        
    def pause_song_if_necessary(self):
        try:
            sp = self.sp
            is_playing = self.update_is_playing(sp)
            if(not is_playing): return

            librespot_device = self.update_librespot_device(sp)
            if(librespot_device is None or not librespot_device.is_active): return

            self.logger.info(f"Spotify is playing on LibreSpot Device")
            
            actual_volume = librespot_device.volume_percent
            self.last_volume = actual_volume
            self.logger.info(f"Actual Volume: {actual_volume}")
            new_volume = int(actual_volume*self.volume_decrease)
            self.logger.info(f"New Volume : {new_volume}")
            sp.volume(new_volume)
            self.wasPaused = True
            time.sleep(0.5)
        except:
            print("[Error] Not able to pause song")

    def play_song(self):
        try:
            sp = self.sp
            if(self.wasPaused):
                #sp.start_playback()
                self.logger.info(f"Setting volumen again to: {self.last_volume}")
                sp.volume(self.last_volume)
                self.wasPaused = False
        except:
            print("[Error] Not able to authorize profile")