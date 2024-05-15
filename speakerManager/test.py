from utils.ConfigurationReader import ConfigurationReader
from services.spotify_service import SpotifyService
import time

config_data = ConfigurationReader().read_config_file()
spotify_service = SpotifyService(config_data)

devices = spotify_service._get_devices()
print(f"devices {devices}")
for device in devices:
    print(device.name)
    print(device.id)

print(spotify_service._update_is_playing())
print(spotify_service._update_librespot_device())
spotify_service.decrease_volume_if_necessary()
time.sleep(2)
#spotify_service.restore_volume()