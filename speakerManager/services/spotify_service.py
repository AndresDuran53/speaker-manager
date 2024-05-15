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
        self.home_spotify_name = spotify_dict.get('librespotName', None)
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
        self.volume_decreased = False
        self.last_volume = 0
        self.volume_decrease_value = 0.8
        self.sp = self._get_spotify_object()

    def _get_spotify_object(self) -> spotipy.Spotify:
        sp = None
        try:
            sp = spotipy.Spotify(retries=0, auth_manager=SpotifyOAuth(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                redirect_uri=self.config.redirect_url,
                scope=self.config.scope))
        except:
            self.logger.error(f"Not able to authorize spotify profile")
        return sp
    
    def _update_is_playing(self, sp: spotipy.Spotify) -> bool:
        if(not self._can_update(self._playing_last_modified,30)): return self._is_spotify_playing

        self.logger.info(f"Updating Spotify is_playing status")
        isPlaying = False
        try:
            playing_track = sp.current_user_playing_track()
            if(playing_track is not None):
                isPlaying = playing_track[u'is_playing']
        except:
            self.logger.error(f"Not able to get spotify song status")
        self._playing_last_modified = datetime.now()
        self._is_spotify_playing = isPlaying  
        return isPlaying
    
    def _get_devices(self, sp: spotipy.Spotify) -> list[SpotifyDevice]:
        spotifyDevice_list = []
        try:
            devices_list = sp.devices()
            spotifyDevice_list = SpotifyDevice.from_json_list(devices_list)
        except:
            self.logger.error(f"Not able to get spotify devices")
        return spotifyDevice_list
    
    def _update_librespot_device(self, sp: spotipy.Spotify) -> SpotifyDevice:
        if(not self._can_update(self._device_last_modified,10)): return self._librespot_device

        self.logger.info(f"Updating Spotify librespot_device object")
        spotifyDevice_list = self._get_devices(sp)
        for spotifyDevice in spotifyDevice_list:
            if(spotifyDevice.name == self.home_spotify_name):
                self._device_last_modified = datetime.now()
                self._librespot_device = spotifyDevice
                return spotifyDevice
        self._device_last_modified = datetime.now()
        self._librespot_device = None
        return None

    def _can_update(self, last_time: datetime, seconds_to_wait: int) -> True:
        if(last_time is None): return True
        current_time = datetime.now()
        time_difference = current_time - last_time
        if time_difference.total_seconds() >= seconds_to_wait:
            return True
        else:
            return False
        
    def is_librespot_playing(self) -> bool:
        sp = self.sp
        is_playing = self._update_is_playing(sp)
        if(not is_playing): return False
        self.logger.info(f"Spotify is playing")

        librespot_device = self._update_librespot_device(sp)
        if(librespot_device is None or not librespot_device.is_active): return False

        self.logger.info(f"Spotify is playing on LibreSpot Device")
        return True
        
    def decrease_volume_if_necessary(self):
        try:
            sp = self.sp
            if(not self.is_librespot_playing()): return

            librespot_device = self._librespot_device            
            actual_volume = librespot_device.volume_percent
            self.last_volume = actual_volume
            self.logger.info(f"Spotify Actual Volume: {actual_volume}")
            new_volume = int(actual_volume*self.volume_decrease_value)
            self.logger.info(f"Spotify New Volume : {new_volume}")
            sp.volume(new_volume)
            self.volume_decreased = True
            time.sleep(0.5)
        except:
            self.logger.error(f"Not able to decrease the spotify volume")

    def restore_volume(self):
        try:
            sp = self.sp
            if(self.volume_decreased):
                #sp.start_playback()
                self.logger.info(f"Setting volumen again to: {self.last_volume}")
                sp.volume(self.last_volume)
                self._librespot_device.volume_percent = self.last_volume
                self.volume_decreased = False
        except:
            self.logger.error(f"Not able to restore the spotify volume")

    def has_to_restore_volume(self):
        if(not self.volume_decreased): return False
        if(self.is_librespot_playing()): return True