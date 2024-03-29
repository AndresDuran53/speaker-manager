from utils.ConfigurationReader import ConfigurationReader
from services.spotify_service import SpotifyService, SpotifyConfig
import time

config_data = ConfigurationReader().read_config_file()
config = SpotifyConfig.from_json(config_data)
spotify_service = SpotifyService(config)

devices = spotify_service.get_devices()
print(f"devices {devices}")
for device in devices:
    print(device.name)
    print(device.id)

print(spotify_service.is_playing())
print(spotify_service.is_raspotify_playing())
spotify_service.pause_song_if_necessary()
time.sleep(2)
#spotify_service.play_song()